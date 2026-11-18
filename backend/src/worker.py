import os,time,json,logging
from pathlib import Path
import redis
from .db import Session
from .models import Estimate,Mould
from .ml import predict_trial
r=redis.Redis.from_url(os.environ['REDIS_URL'],decode_responses=True)
Path('/artifacts').mkdir(exist_ok=True)
while True:
    Path('/tmp/worker-heartbeat').touch()
    entry=r.blpop('mould-estimates',timeout=2)
    if not entry: continue
    eid=int(entry[1])
    with Session() as s:
        e=s.get(Estimate,eid)
        if not e or e.status!='calculating':continue
        try:
            e.predicted_hours,e.model_result=predict_trial(s,s.get(Mould,e.mould_id),e.setup_hours)
            e.status='estimated'
            Path(f'/artifacts/estimate-{eid}.json').write_text(json.dumps(e.model_result,ensure_ascii=False))
        except Exception as ex:
            logging.exception('estimate failed');e.status='failed';e.model_result={'error':str(ex)}
        s.commit()
