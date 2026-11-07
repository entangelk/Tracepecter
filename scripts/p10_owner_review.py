"""P10-02 (DB-09 R1): build a verdict-blind owner page for boundary-crossing confirmed/unconfirmed pairs."""
import argparse
import base64
import io
import json
from pathlib import Path

from PIL import Image, ImageOps

from scripts.p09_group_candidates import read_csv, sha256, write_csv, write_json

AUDIT = Path('experiments/p08_anonymized/leakage_audit/image_audit.jsonl')
VERDICTS = ('confirmed_same_look', 'different_look', 'unconfirmed')

PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>P10 같은 룩 확인</title>
<style>body{font-family:sans-serif;margin:16px;background:#f4f4f4}.pair{background:#fff;margin:0 0 24px;padding:12px;border-radius:8px}
.imgs{display:flex;gap:8px;flex-wrap:wrap}.imgs figure{margin:0;flex:1 1 300px}.imgs img{width:100%;height:auto}
label{margin-right:16px}input[type=text]{width:100%;margin-top:8px}button{font-size:16px;padding:8px 16px}</style></head><body>
<h1>P10 같은 룩 확인 (<span id="n"></span>쌍)</h1>
<p>두 사진이 <b>같은 옷차림을 같은 촬영에서 찍은 다른 컷</b>이면 "같은 룩"을 고릅니다. 비슷한 옷이라도 촬영 세트·소품·코디가 다르면 "다른 룩"입니다. 확신이 없으면 "판단 보류"를 고릅니다. 모든 쌍을 고른 뒤 아래 <b>CSV 저장</b>을 누르세요. 페이지를 닫으면 선택이 초기화됩니다.</p>
<div id="list"></div><button id="save">CSV 저장</button> <span id="msg"></span>
<script>
const CASES=/*CASES*/null;
const L={confirmed_same_look:'같은 룩',different_look:'다른 룩',unconfirmed:'판단 보류'};
document.getElementById('n').textContent=CASES.length;
const list=document.getElementById('list');
CASES.forEach((c,i)=>{const d=document.createElement('div');d.className='pair';
d.innerHTML=`<h3>${i+1}. ${c.a} / ${c.b}</h3><div class="imgs"><figure><img src="${c.img_a}"><figcaption>${c.a}</figcaption></figure><figure><img src="${c.img_b}"><figcaption>${c.b}</figcaption></figure></div>`+
Object.keys(L).map(v=>`<label><input type="radio" name="p${i}" value="${v}"> ${L[v]}</label>`).join('')+`<input type="text" id="note${i}" placeholder="메모(선택)">`;
list.appendChild(d)});
document.getElementById('save').onclick=()=>{const rows=[];
for(let i=0;i<CASES.length;i++){const r=document.querySelector(`input[name=p${i}]:checked`);
if(!r){document.getElementById('msg').textContent=`${i+1}번이 비어 있습니다`;return}
rows.push([CASES[i].a,CASES[i].b,r.value,'"'+document.getElementById('note'+i).value.replace(/"/g,'""')+'"'].join(','))}
const blob=new Blob(['a,b,owner_verdict,note\\n'+rows.join('\\n')+'\\n'],{type:'text/csv'});
const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='p10_owner_answers.csv';a.click();
document.getElementById('msg').textContent='저장했습니다'};
</script></body></html>
"""


def owner_pairs(rows):
    """Boundary-crossing pairs whose agent verdict is not a plain different-look."""
    return [r for r in rows if r['split_a'] != r['split_b'] and r['verdict'] != 'different_look']


def encode(path):
    with Image.open(path) as image:
        thumb = ImageOps.contain(image.convert('RGB'), (800, 1000))
    buffer = io.BytesIO()
    thumb.save(buffer, 'JPEG', quality=90)
    return 'data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviews', type=Path, nargs='+', required=True)
    parser.add_argument('--pending', type=Path, required=True, help='tracked CSV of pairs sent to the owner')
    parser.add_argument('--page', type=Path, required=True)
    parser.add_argument('--image-root', type=Path, required=True)
    args = parser.parse_args()
    if args.pending.exists() or args.page.exists():
        raise ValueError('output exists; never overwrite owner review inputs')
    rows = owner_pairs([r for path in args.reviews for r in read_csv(path)])
    meta = {r['image_id']: r for r in read_csv('data/versions/p09_r1/metadata.csv')}
    images = {r['image_id']: r for r in map(json.loads, AUDIT.read_text().splitlines())}
    cases = []
    for r in rows:
        case = dict(a=r['a'], b=r['b'])
        for key in ('a', 'b'):
            path = args.image_root/Path(meta[r[key]]['path']).relative_to('images')
            if sha256(path) != images[r[key]]['sha256']:
                raise ValueError(f'original image hash mismatch: {r[key]}')
            case['img_'+key] = encode(path)
        cases.append(case)
    args.page.parent.mkdir(parents=True, exist_ok=True)
    args.page.write_text(PAGE.replace('/*CASES*/null', json.dumps(cases).replace('</', '<\\/')), encoding='utf-8')
    write_csv(args.pending, rows, list(rows[0]))
    write_json(args.pending.with_suffix('.lock.json'), dict(
        source_sha256=sha256(__file__), reviews_sha256={str(p): sha256(p) for p in args.reviews},
        pending_sha256=sha256(args.pending), page_sha256=sha256(args.page)))
    print(f'{len(rows)} pairs for owner review: {args.page}')


if __name__ == '__main__':
    main()
