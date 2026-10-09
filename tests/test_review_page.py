"""P06-03 정적 검토 페이지: 데이터가 정확히 한 번 주입되고, 기존 판정·원본 이미지가 함께 실린다."""
import json

import pytest
from PIL import Image

from scripts.build_review_page import build, load_cases


def test_build_embeds_cases_reviews_and_copies_originals(tmp_path):
    (tmp_path/'set.csv').write_text('image_id,case_type,label,category,generator,split,owner_check,scores\n'
                                    'g1,false_positive,0,상의,sdxl,test,True,"{""original"": 80.0}"\n', encoding='utf-8')
    (tmp_path/'meta.csv').write_text('image_id,path\ng1,images/generated/g1.png\n', encoding='utf-8')
    (tmp_path/'owner.csv').write_text('image_id,perceived,cues,agent_agreement,note,updated_at\n'
                                      'g1,ambiguous,full_body,,"메모, </script> 포함",2026-10-09T00:00:00+00:00\n',
                                      encoding='utf-8')
    (tmp_path/'src/generated').mkdir(parents=True)
    Image.new('RGB', (4, 4)).save(tmp_path/'src/generated/g1.png')
    cases = load_cases(tmp_path/'set.csv', tmp_path/'meta.csv', tmp_path/'agent.csv', tmp_path/'owner.csv')
    page = build(cases, tmp_path/'src', tmp_path/'out')
    html = page.read_text(encoding='utf-8')
    assert '/*REVIEW_DATA*/' not in html and html.count('</script>') == 1   # 메모의 </script>가 페이지를 깨지 않음
    payload = html.split('const DATA = ', 1)[1].split(';\nconst splitCues', 1)[0]
    data = json.loads(payload.replace('<\\/', '</'))
    [case] = data['cases']
    assert case['file'] == 'g1.png' and case['owner_check'] is True and case['agent'] is None
    assert case['review']['perceived'] == 'ambiguous' and case['review']['note'] == '메모, </script> 포함'
    assert (tmp_path/'out/img/g1.png').read_bytes() == (tmp_path/'src/generated/g1.png').read_bytes()


def test_build_rejects_template_without_placeholder(tmp_path, monkeypatch):
    import scripts.build_review_page as module
    template = tmp_path/'t.html'
    template.write_text('<script>const DATA = {};</script>')
    monkeypatch.setattr(module, 'TEMPLATE', template)
    with pytest.raises(ValueError):
        build([], tmp_path, tmp_path/'out')
