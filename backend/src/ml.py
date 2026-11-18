import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from .models import TrialHistory
from sqlalchemy import select
STEEL={'P20':0,'H13':1,'S136':2}
def vector(x): return [x.cavities,x.slides,x.weight_kg,STEEL[x.steel]]
def predict_trial(s,mould,setup):
    rows=s.scalars(select(TrialHistory).order_by(TrialHistory.id)).all()
    if len(rows)<30: raise ValueError('完成试模样本少于 30 条，不能估价')
    x=np.array([vector(r) for r in rows]); y=np.array([r.actual_hours for r in rows])
    a,b,c,d=train_test_split(x,y,test_size=.2,random_state=42)
    model=make_pipeline(PolynomialFeatures(degree=2,interaction_only=True,include_bias=False),StandardScaler(),Ridge(alpha=3.0))
    model.fit(a,c)
    pred=max(.5,float(model.predict([vector(mould)])[0]))+setup
    mae=float(mean_absolute_error(d,model.predict(b)))
    names=model[0].get_feature_names_out(['模腔','滑块','重量','钢材'])
    coeff=sorted(zip(names,model[-1].coef_),key=lambda x:abs(x[1]),reverse=True)
    return round(pred,2),{'mae_hours':round(mae,3),'training_rows':len(a),'holdout_rows':len(b),'seed':42,'alpha':3,'features':[{'name':n,'coefficient':round(float(v),3)} for n,v in coeff], 'validation':[{'actual':round(float(t),2),'predicted':round(float(p),2)} for t,p in zip(d,model.predict(b))], 'note':'系数来自标准化后的交叉特征，仅解释统计关系；预测包含本单准备工时。'}
