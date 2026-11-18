import random
from sqlalchemy import select, func
from src.db import Base,engine,Session
from src.models import User,Mould,MachineSlot,Estimate,TrialHistory
from src.execution_models import TrialExecution,CostReview
from src.workshop_models import MaintenanceWindow,ResinLot,TrialMaterial,ReviewMaterialLedger,TrialDelivery
from src.switch_models import MachineSwitchRequest
from src.auth import hash_password

def seed():
    Base.metadata.create_all(engine)
    with Session() as s:
        for role in ('admin','estimator','viewer'):
            if not s.scalar(select(User).where(User.email==role+'@ruimo.demo')): s.add(User(email=role+'@ruimo.demo',role=role,password_hash=hash_password('Mould2026!')))
        for code,name,cav,slides,steel,kg in [('MD-86','八腔医疗接头模',8,4,'S136',860),('MD-42','双腔仪表外壳模',2,2,'P20',420),('MD-115','十六腔盖件模',16,6,'H13',1150)]:
            if not s.scalar(select(Mould).where(Mould.code==code)): s.add(Mould(code=code,name=name,cavities=cav,slides=slides,steel=steel,weight_kg=kg))
        s.flush()
        for machine,start,cap in [('M280','2026-11-18 08:00',48),('M280','2026-11-19 08:00',4),('M450','2026-11-18 08:00',72),('M580','2026-11-20 08:00',72),('M280','2026-11-20 08:00',60)]:
            if not s.scalar(select(MachineSlot).where(MachineSlot.machine==machine,MachineSlot.start_hour==start)): s.add(MachineSlot(machine=machine,start_hour=start,capacity_hours=cap,reserved_hours=0))
        rng=random.Random(42)
        for i in range(160):
            code=f'TR-{i+1:03d}'
            if s.scalar(select(TrialHistory).where(TrialHistory.trial_code==code)):continue
            cav=rng.choice([2,4,8,16]);sl=rng.randint(0,8);kg=rng.uniform(180,1600);steel=rng.choice(['P20','H13','S136'])
            hours=2+cav*.3+sl*.65+kg*.004+cav*sl*.035+(['P20','H13','S136'].index(steel))*.8+rng.gauss(0,.4)
            s.add(TrialHistory(trial_code=code,cavities=cav,slides=sl,steel=steel,weight_kg=round(kg,1),actual_hours=round(hours,2)))
        s.flush()
        if not s.scalar(select(Estimate).where(Estimate.code=='QE-26017')):
            m=s.scalar(select(Mould).where(Mould.code=='MD-86'))
            s.add(Estimate(code='QE-26017',mould_id=m.id,rate=280,setup_hours=2,quote_amount=8000,status='draft'))
        s.flush()
        if not s.scalar(select(Estimate).where(Estimate.code=='QE-FLOOR-DEMO')):
            m=s.scalar(select(Mould).where(Mould.code=='MD-42'));slot=s.scalar(select(MachineSlot).where(MachineSlot.machine=='M450'))
            s.add(Estimate(code='QE-FLOOR-DEMO',mould_id=m.id,slot_id=slot.id,rate=300,setup_hours=1,predicted_hours=10,quote_amount=5000,status='committed',model_result={'note':'已承诺的演示订单，供实绩采集；不作模型效果指标'}));slot.reserved_hours+=10
        # Signed history across all three presses: the machine-switch learner only
        # trusts finished+signed actuals. Machine bias is real in this demo data, so
        # complexity-adjusted machine effects are recoverable instead of being an
        # artefact of which press got the easy moulds.
        hist_slots={}
        for machine,start,cap in [('M280','2026-09-01 08:00',200),('M450','2026-09-01 08:00',200),('M580','2026-09-01 08:00',200)]:
            slot=s.scalar(select(MachineSlot).where(MachineSlot.machine==machine,MachineSlot.start_hour==start))
            if not slot: slot=MachineSlot(machine=machine,start_hour=start,capacity_hours=cap,reserved_hours=0);s.add(slot);s.flush()
            hist_slots[machine]=slot
        steel_idx={'P20':0,'H13':1,'S136':2}
        machine_bias={'M280':1.6,'M450':0.3,'M580':-1.1}
        demo_moulds=[('MD-86',8,4,'S136',860),('MD-42',2,2,'P20',420),('MD-115',16,6,'H13',1150),
                     ('MD-205',4,2,'P20',360),('MD-218',8,6,'H13',980),('MD-233',16,4,'S136',1320)]
        hist_rng=random.Random(20261118)
        for i in range(18):
            code=f'QE-HIST-{i+1:03d}'
            if s.scalar(select(Estimate).where(Estimate.code==code)):continue
            mc,cav,sl,steel,kg=demo_moulds[i%len(demo_moulds)]
            mould=s.scalar(select(Mould).where(Mould.code==mc))
            if not mould:
                mould=Mould(code=mc,name=f'历史试模 {mc}',cavities=cav,slides=sl,steel=steel,weight_kg=kg);s.add(mould);s.flush()
            # Independent draw keeps press choice separate from mould complexity,
            # otherwise the fixed effect would be unidentifiable (the exact
            # "big press only gets easy moulds" trap the learner must correct).
            machine=hist_rng.choice(('M280','M450','M580'))
            base=2+cav*.3+sl*.65+kg*.004+cav*sl*.035+steel_idx[steel]*.8
            hours=max(0.8,round(base+machine_bias[machine]+hist_rng.gauss(0,.25),2))
            rate=280;pred=round(base+1.0,2);quote=round(pred*rate*1.3,2)
            slot=hist_slots[machine];slot.reserved_hours=round(slot.reserved_hours+pred,2)
            est=Estimate(code=code,mould_id=mould.id,slot_id=slot.id,rate=rate,setup_hours=1,predicted_hours=pred,quote_amount=quote,status='committed')
            s.add(est);s.flush()
            ex=TrialExecution(estimate_id=est.id,started_at=f'2026-09-{10+i//3:02d}T00:00:00+00:00',ended_at=f'2026-09-{10+i//3:02d}T{int(hours):02d}:00:00+00:00',actual_hours=hours,good_shots=96,total_shots=100,snapshot={'estimate_code':code,'predicted_hours':pred,'quoted_amount':quote,'rate':rate,'mould_code':mc,'slot_id':slot.id},status='completed')
            s.add(ex);s.flush()
            material=120.0;actual=round(hours*rate+material,2);delta=round(hours-pred,4)
            rev=CostReview(execution_id=ex.id,material_cost=material,actual_cost=actual,quoted_amount=quote,variance_hours=delta,variance_pct=round(delta/pred*100,3),margin=round(quote-actual,2),reason='历史签结样本，用于换机机台倾向学习',status='signed',signed_by='admin@ruimo.demo')
            s.add(rev)
        s.flush()
        # Committed, not started: candidate for the switch-evaluation page.
        if not s.scalar(select(Estimate).where(Estimate.code=='QE-SWITCH-DEMO')):
            m=s.scalar(select(Mould).where(Mould.code=='MD-86'))
            src=s.scalar(select(MachineSlot).where(MachineSlot.machine=='M280',MachineSlot.start_hour=='2026-11-18 08:00'))
            pred=12.0;rate=280
            s.add(Estimate(code='QE-SWITCH-DEMO',mould_id=m.id,slot_id=src.id,rate=rate,setup_hours=2,predicted_hours=pred,quote_amount=round(pred*rate*1.3,2),status='committed',model_result={'note':'换机评估演示单；原估价回归保留'}));src.reserved_hours=round(src.reserved_hours+pred,2)
        # Out-of-distribution mould: deliberately no comparable signed samples, so
        # the learner must refuse rather than invent a recommendation.
        if not s.scalar(select(Mould).where(Mould.code=='MD-999')):
            s.add(Mould(code='MD-999',name='超大模腔试制模',cavities=64,slides=32,steel='S136',weight_kg=1980));s.flush()
        if not s.scalar(select(Estimate).where(Estimate.code=='QE-NOCOMP-DEMO')):
            m=s.scalar(select(Mould).where(Mould.code=='MD-999'))
            src=s.scalar(select(MachineSlot).where(MachineSlot.machine=='M450',MachineSlot.start_hour=='2026-11-18 08:00'))
            pred=40.0;rate=280
            s.add(Estimate(code='QE-NOCOMP-DEMO',mould_id=m.id,slot_id=src.id,rate=rate,setup_hours=4,predicted_hours=pred,quote_amount=round(pred*rate*1.3,2),status='committed',model_result={'note':'缺可比样本拒绝推荐演示单'}));src.reserved_hours=round(src.reserved_hours+pred,2)
        for code,grade,qty,price,state in [('RS-P20-DEMO','ABS自然色',500,20,'available'),('RS-ISOLATED','ABS复检隔离',50,18,'quarantine')]:
            if not s.scalar(select(ResinLot).where(ResinLot.code==code)):
                s.add(ResinLot(code=code,grade=grade,received_kg=qty,available_kg=qty,unit_price=price,state=state))
        s.commit()
        print({t.__tablename__:s.scalar(select(func.count()).select_from(t)) for t in (User,Mould,MachineSlot,Estimate,TrialHistory,TrialExecution,CostReview,MaintenanceWindow,ResinLot,TrialMaterial,ReviewMaterialLedger,TrialDelivery,MachineSwitchRequest)})
if __name__=='__main__':seed()
