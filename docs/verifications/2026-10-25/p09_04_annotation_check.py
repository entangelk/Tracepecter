import csv, collections
D='/app/experiments/p09_leakage_repair/r1/diagnostic/'
P8='/app/experiments/p08_anonymized/diagnostic/'
def rd(p): 
    with open(p,newline='') as f: return list(csv.DictReader(f))
def conv(x): return 0 if x<=1 else 1
# P08 precedent conversion
f8={r['image_id']:r for r in rd(P8+'face_review_owner_features.csv')}
o8={r['image_id']:r for r in rd(P8+'face_review_owner.csv')}
assert f8.keys()==o8.keys(), 'p08 keys'
bad8=[k for k in f8 if (conv(int(f8[k]['visible_faces'])),conv(int(f8[k]['uncovered_visible_faces'])))!=(int(o8[k]['visible_faces']),int(o8[k]['uncovered_visible_faces']))]
print('p08 rows',len(f8),'conv mismatch',bad8)
print('p08 feature pairs',collections.Counter((r['visible_faces'],r['uncovered_visible_faces']) for r in f8.values()))
feat=rd(D+'face_review_owner_new_features.csv'); new=rd(D+'face_review_owner_new.csv')
print('features rows',len(feat),'new rows',len(new), 'ids unique',len({r['image_id'] for r in feat}))
print('feature pairs',collections.Counter((r['visible_faces'],r['uncovered_visible_faces']) for r in feat))
fm={r['image_id']:r for r in feat}; nm={r['image_id']:r for r in new}
assert [r['image_id'] for r in feat]==[r['image_id'] for r in new]
bad=[k for k in fm if (conv(int(fm[k]['visible_faces'])),conv(int(fm[k]['uncovered_visible_faces'])))!=(int(nm[k]['visible_faces']),int(nm[k]['uncovered_visible_faces']))]
print('conv mismatch',bad)
rng=[k for k in fm if not(0<=int(fm[k]['visible_faces'])<=4 and 0<=int(fm[k]['uncovered_visible_faces'])<=4)]
print('feature out of range',rng)
viol=[k for k in fm if int(fm[k]['uncovered_visible_faces'])>int(fm[k]['visible_faces'])]
print('feature uncovered>visible',viol)
# uncovered features in 2..4 while visible maps... check edge: uncovered>=2 visible>=2
pend=[r['image_id'] for r in rd(D+'face_review_owner_pending.csv')]
print('pending',len(pend),'set eq',set(pend)==set(fm),'order eq',pend==[r['image_id'] for r in feat])
reu=rd(D+'face_review_owner_reused.csv'); own=rd(D+'face_review_owner.csv'); chk=rd(D+'face_review_owner_check.csv')
print('reused',len(reu),'owner',len(own),'check',len(chk))
om={r['image_id']:r for r in own}
comb={**{r['image_id']:r for r in reu},**nm}
print('reused∩new',len(set(r['image_id'] for r in reu)&set(nm)))
print('owner == reused+new', om.keys()==comb.keys() and all(om[k]==comb[k] for k in om))
print('check ids == owner ids', {r['image_id'] for r in chk}==set(om), collections.Counter(r['reason'] for r in chk))
# reused vs P08 owner
bad_reu=[r['image_id'] for r in reu if r['image_id'] not in o8 or (o8[r['image_id']]['visible_faces'],o8[r['image_id']]['uncovered_visible_faces'])!=(r['visible_faces'],r['uncovered_visible_faces'])]
print('reused not equal to P08 owner',bad_reu)
ag={r['image_id']:r for r in rd(D+'face_review_agent.csv')}; fr=rd(D+'face_review.csv'); fm2={r['image_id']:r for r in fr}
tmpl=[r['image_id'] for r in rd(D+'face_review_template.csv')]
print('face_review',len(fr),'ids==agent',set(fm2)==set(ag),'ids==template',[r['image_id'] for r in fr]==tmpl)
mis=[]; ch=[]
for k,r in fm2.items():
    src=om.get(k,ag[k]); 
    if (r['visible_faces'],r['uncovered_visible_faces'])!=(src['visible_faces'],src['uncovered_visible_faces']): mis.append(k)
    if (r['visible_faces'],r['uncovered_visible_faces'])!=(ag[k]['visible_faces'],ag[k]['uncovered_visible_faces']): ch.append(k)
print('merge mismatch',mis); print('changed vs agent',len(ch),ch)
print('confirmed all 1',all(r['confirmed']=='1' for r in fr))
print('range ok',all(0<=int(r['uncovered_visible_faces'])<=int(r['visible_faces']) for r in fr))
def st(r):
    v,u=int(r['visible_faces']),int(r['uncovered_visible_faces'])
    return 'missed' if u>=1 else ('no_visible' if v==0 else 'anonymized')
print('states',collections.Counter(st(r) for r in fr))
for k in ch: print(k,'agent',ag[k]['visible_faces'],ag[k]['uncovered_visible_faces'],'final',fm2[k]['visible_faces'],fm2[k]['uncovered_visible_faces'],'feat',fm.get(k,{}).get('visible_faces'),fm.get(k,{}).get('uncovered_visible_faces'), 'reused' if k not in nm else 'new')
