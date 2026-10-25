"""Independent recomputation of P09-04 diagnostic gates (no project imports)."""
import csv, json, math, hashlib, random, sys
from collections import Counter
import numpy as np
R='/app/'
D=R+'experiments/p09_leakage_repair/r1/diagnostic/'
def rd(p):
    with open(p,newline='') as f: return list(csv.DictReader(f))
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
cfg=__import__('yaml').safe_load(open(R+'configs/p09_r1_diagnostic.yaml'))
res=json.load(open(D+'result.json'))
cal=json.load(open(R+'experiments/p09_leakage_repair/r1/calibration/calibration.json'))
bcal=json.load(open(R+'experiments/p05_calibration/calibration.json'))
meta={r['image_id']:r for r in rd(R+'data/versions/p09_r1/metadata.csv')}
print('splits',Counter((r['split'],r['label']) for r in meta.values()))
# prediction files
preds={}
for name in ['baseline_original','baseline_anonymized','candidate_original','candidate_anonymized','candidate_real_shape','candidate_real_size','candidate_gen_gray','candidate_gen_restore']:
    p=D+name+'.csv'; rows=rd(p); ids=[r['image_id'] for r in rows]
    assert len(ids)==len(set(ids)), name
    v={r['image_id']:float(r['logit']) for r in rows}
    assert all(math.isfinite(x) for x in v.values())
    preds[name]=v
    print(name,len(v),'sha_ok',sha(p)==res['prediction_sha256'][name+'.csv'])
eval_ids={i for i,r in meta.items() if r['split'] in ('val','test','test_unseen')}
real_ids=[r['image_id'] for r in rd(D+'real_interventions.csv')]
real_set=set(real_ids); gen_ids=[r['image_id'] for r in rd(D+'gen_interventions.csv')]
print('real manifest rows',len(real_ids),'unique images',len(real_set),'all train real',all(meta[i]['split']=='train' and meta[i]['label']=='1' for i in real_set))
print('gen manifest',len(gen_ids),len(set(gen_ids)),Counter(meta[i]['generator'] for i in gen_ids), all(meta[i]['label']=='0' and meta[i]['split'] in('test','test_unseen') for i in gen_ids))
gm={r['image_id']:r for r in rd(D+'gen_interventions.csv')}
print('gen manifest generator/split consistent',all(gm[i]['generator']==meta[i]['generator'] and gm[i]['split']==meta[i]['split'] for i in gen_ids))
for k in ['baseline_original','baseline_anonymized','candidate_original']: print(k,'ids==eval',set(preds[k])==eval_ids)
print('cand anon ids == eval|real',set(preds['candidate_anonymized'])==eval_ids|real_set, 'real∩eval',len(real_set&eval_ids))
for k in ['candidate_real_shape','candidate_real_size']: print(k,set(preds[k])==real_set)
for k in ['candidate_gen_gray','candidate_gen_restore']: print(k,set(preds[k])==set(gen_ids))
# eligibility of gen sample
cache={r['image_id']:json.loads(r['boxes']) for r in rd(R+'experiments/p08_anonymized/face_boxes.csv')}
elig=sorted(i for i,r in meta.items() if r['label']=='0' and r['split'] in ('test','test_unseen') and len(cache[i])>0)
print('eligible per gen',Counter(meta[i]['generator'] for i in elig), 'sample subset of eligible',set(gen_ids)<=set(elig))
def sig(x,T): return 1/(1+math.exp(-x/T)) if x/T>=0 else math.exp(x/T)/(1+math.exp(x/T))
T,thr=cal['temperature'],cal['threshold_probability']
def auc(y,p):
    pos=[q for a,q in zip(y,p) if a==1]; neg=[q for a,q in zip(y,p) if a==0]
    s=0.
    for q in pos:
        s+=sum(1. if q>n else .5 if q==n else 0. for n in neg)
    return s/len(pos)/len(neg)
def ap(y,p):
    order=sorted(range(len(p)),key=lambda k:-p[k]); tp=0; s=0; P=sum(y)
    # handle ties by grouping
    i=0; prev_r=0; fp=0
    while i<len(order):
        j=i
        while j<len(order) and p[order[j]]==p[order[i]]: j+=1
        for k in order[i:j]:
            if y[k]==1: tp+=1
            else: fp+=1
        r=tp/P; prec=tp/(tp+fp); s+=(r-prev_r)*prec; prev_r=r; i=j
    return s
def cohort(name):
    if name=='val': return [i for i in meta if meta[i]['split']=='val']
    if name=='standard': return [i for i in meta if meta[i]['split']=='test']
    return [i for i in meta if (meta[i]['split']=='test' and meta[i]['label']=='1') or meta[i]['split']=='test_unseen']
def metrics(ids,logits,T,thr):
    y=[int(meta[i]['label']) for i in ids]; p=[sig(logits[i],T) for i in ids]
    pred=[int(q>=thr) for q in p]; tp=sum(a==1 and b==1 for a,b in zip(y,pred)); fp=sum(a==0 and b==1 for a,b in zip(y,pred)); fn=sum(a==1 and b==0 for a,b in zip(y,pred))
    prec=tp/(tp+fp); rec=tp/(tp+fn)
    eps=1e-15
    nll=-sum(math.log(max(q,eps)) if a else math.log(max(1-q,eps)) for a,q in zip(y,p))/len(y)
    brier=sum((q-a)**2 for a,q in zip(y,p))/len(y)
    ece=0
    for b in range(10):
        idx=[k for k,q in enumerate(p) if (b/10<q<=(b+1)/10) or (b==0 and q==0)]
        if idx: ece+=len(idx)/len(p)*abs(sum(y[k] for k in idx)/len(idx)-sum(p[k] for k in idx)/len(idx))
    return dict(n=len(y),roc_auc=auc(y,p),pr_auc=ap(y,p),accuracy=sum(a==b for a,b in zip(y,pred))/len(y),precision=prec,recall=rec,f1=2*prec*rec/(prec+rec),nll=nll,brier=brier,ece=ece)
maxdiff={}
for model,c in [('baseline',bcal),('candidate',cal)]:
    for inp in ['original','anonymized']:
        stored=res['evaluation'][model][inp]
        assert stored['temperature']==c['temperature'] and stored['threshold_probability']==c['threshold_probability']
        for co in ['val','standard','unseen']:
            m=metrics(cohort(co),preds[f'{model}_{inp}'],c['temperature'],c['threshold_probability'])
            s=stored['cohorts'][co]
            d={k:abs(m[k]-s[k]) for k in m if k!='n'}
            print(model,inp,co,'n',m['n'],'auc',round(m['roc_auc'],10),'maxdiff',{k:f'{v:.1e}' for k,v in d.items() if v>1e-9} or 'all<1e-9')
print('cohort sizes',{c:len(cohort(c)) for c in ['val','standard','unseen']})
# probabilities candidate
P={k[len('candidate_'):]:{i:sig(x,T) for i,x in v.items()} for k,v in preds.items() if k.startswith('candidate_')}
ref=P['anonymized']
z=1.959963984540054
def wil(e,n):
    p=e/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (max(0,c-h),min(1,c+h))
def newc(e1,n1,e2,n2):
    p1,p2=e1/n1,e2/n2; l1,u1=wil(e1,n1); l2,u2=wil(e2,n2)
    d=p1-p2; return (d-math.sqrt((p1-l1)**2+(u2-p2)**2), d+math.sqrt((u1-p1)**2+(p2-l2)**2))
fr=rd(D+'face_review.csv')
st={'anonymized':[], 'no_visible_face':[], 'missed_visible_face':[]}
for r in fr:
    v,u=int(r['visible_faces']),int(r['uncovered_visible_faces'])
    st['missed_visible_face' if u>0 else 'no_visible_face' if v==0 else 'anonymized'].append(r['image_id'])
S={}
for s,ids in st.items():
    e=sum(ref[i]>=thr for i in ids); S[s]=(e,len(ids)); 
    print('state',s,e,'/',len(ids),'wilson',wil(e,len(ids)),'stored',res['gates']['face_concentration']['states'][s]['false_positives'],res['gates']['face_concentration']['states'][s]['ci'])
fc_ok=all(n>=20 for e,n in S.values())
for a,b in cfg['face_concentration']['comparisons']:
    ci=newc(*S[a],*S[b]); ok=ci[0]>=-0.1 and ci[1]<=0.1; fc_ok&=ok
    print('cmp',a,b,'diff',S[a][0]/S[a][1]-S[b][0]/S[b][1],'ci',ci,'pass',ok)
print('face_concentration pass',fc_ok)
# P08-style borderline sensitivity: how many extra FP needed to fail
seed=cfg['seed']
gates={'face_concentration':fc_ok}
for cond,ids in [('real_shape',sorted(real_set)),('real_size',sorted(real_set)),('gen_gray',sorted(gen_ids)),('gen_restore',sorted(gen_ids))]:
    n=len(ids); r_=np.array([ref[i] for i in ids]); v_=np.array([P[cond][i] for i in ids]); y=np.array([int(meta[i]['label']) for i in ids])
    a=np.abs(v_-r_)*100
    g=np.random.Generator(np.random.PCG64(seed)); idx=g.integers(0,n,size=(20000,n))
    lo,hi=np.percentile(a[idx].mean(axis=1),[2.5,97.5],method='linear')
    cr=(r_>=thr)==y; cv=(v_>=thr)==y; harm=int((cr&~cv).sum()); rev=int((~cr&cv).sum())
    wu=wil(harm,n)[1]; ok=n>=80 and hi<=5 and wu<=0.05; gates[cond]=ok
    s=res['gates'][cond]
    # order sensitivity: shuffle order with other seeds
    alt=[]
    for k in range(5):
        perm=np.random.default_rng(k).permutation(n); aa=a[perm]
        g2=np.random.Generator(np.random.PCG64(seed)); ii=g2.integers(0,n,size=(20000,n)); alt.append(np.percentile(aa[ii].mean(axis=1),97.5))
    print(cond,'n',n,'mean_abs',a.mean(),'ci',(lo,hi),'stored',s['absolute_shift_ci'],'harm',harm,'rev',rev,'wilson_up',wu,'stored',s['error_ci'][1],'pass',ok,'| alt-order upper max',max(alt))
    print('   ref-correct count',int(cr.sum()),'/',n)
sa=metrics(cohort('standard'),preds['candidate_anonymized'],T,thr)['roc_auc']; ua=metrics(cohort('unseen'),preds['candidate_anonymized'],T,thr)['roc_auc']
adopt=sa>=0.9 and ua>=0.8 and all(gates.values())
print('AUC A',sa,'B',ua,'gates',gates,'adopt',adopt,'stored',res['adoption']['adopt'])

# --- annotation sensitivity (agent-only vs final) ---

D='/app/experiments/p09_leakage_repair/r1/diagnostic/'
T=0.7770388872932664; thr=0.23513432654393307
lg={r['image_id']:float(r['logit']) for r in csv.DictReader(open(D+'candidate_anonymized.csv'))}
p={i:1/(1+math.exp(-x/T)) for i,x in lg.items()}
z=1.959963984540054
def wil(e,n):
    q=e/n; d=1+z*z/n; c=(q+z*z/(2*n))/d; h=z*math.sqrt(q*(1-q)/n+z*z/(4*n*n))/d; return c-h,c+h
def run(f,label):
    S={'a':[0,0],'n':[0,0],'m':[0,0]}
    for r in csv.DictReader(open(D+f)):
        v,u=int(r['visible_faces']),int(r['uncovered_visible_faces']); s='m' if u else 'n' if v==0 else 'a'
        S[s][1]+=1; S[s][0]+=p[r['image_id']]>=thr
    out=[]
    for a,b in [('a','n'),('a','m'),('n','m')]:
        (e1,n1),(e2,n2)=S[a],S[b]; p1,p2=e1/n1,e2/n2; l1,u1=wil(e1,n1); l2,u2=wil(e2,n2)
        out.append((a,b,round(p1-p2-math.hypot(p1-l1,u2-p2),4),round(p1-p2+math.hypot(u1-p1,p2-l2),4)))
    print(label,S,out)
run('face_review_agent.csv','agent-only')
run('face_review.csv','final')
# FP among changed rows
for i in ['gen_000006','gen_000064','gen_000173','gen_000179','gen_000210','gen_000737','gen_001035','gen_001120','gen_001532','gen_001548','gen_002541','gen_002602','gen_002625','gen_002870']:
    if p[i]>=thr: print('changed row FP',i,p[i])
