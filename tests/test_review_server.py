"""P06-03 검토 저장: 부분 갱신이 기존 판정을 지우지 않고, 잘못된 값·사례 밖 ID는 거부한다."""
import csv

import pytest

from scripts.review_server import load_cases, read_reviews, save_review


def test_save_review_merges_and_validates(tmp_path):
    path = tmp_path/'owner.csv'
    valid = {'a', 'b'}
    save_review(path, 'a', dict(perceived='ambiguous'), valid)
    save_review(path, 'a', dict(cues=['face_hidden', 'full_body']), valid)
    row = save_review(path, 'a', dict(note='소매 경계'), valid)
    assert row['perceived'] == 'ambiguous'                    # 부분 갱신이 이전 필드를 보존
    assert row['cues'] == 'full_body|face_hidden'             # 정의 순서로 정규화
    save_review(path, 'a', dict(perceived=''), valid)         # 선택 해제 허용
    assert read_reviews(path)['a']['perceived'] == '' and read_reviews(path)['a']['note'] == '소매 경계'
    for image_id, patch in [('z', dict(perceived='ambiguous')), ('a', dict(perceived='real')),
                            ('a', dict(cues=['unknown'])), ('a', dict(score=1))]:
        with pytest.raises(ValueError):
            save_review(path, image_id, patch, valid)
    assert set(read_reviews(path)) == {'a'}


def test_load_cases_joins_paths_and_reviews(tmp_path):
    (tmp_path/'set.csv').write_text('image_id,case_type,label,category,generator,split,owner_check,scores\n'
                                    'g1,false_positive,0,상의,sdxl,test,True,"{""original"": 80.0}"\n', encoding='utf-8')
    (tmp_path/'meta.csv').write_text('image_id,path\ng1,images/generated/g1.png\n', encoding='utf-8')
    save_review(tmp_path/'agent.csv', 'g1', dict(perceived='photo_like'), {'g1'})
    [case] = load_cases(tmp_path/'set.csv', tmp_path/'meta.csv', tmp_path/'agent.csv', tmp_path/'owner.csv')
    assert case['owner_check'] is True and case['label'] == 0 and case['scores'] == {'original': 80.0}
    assert case['path'] == 'images/generated/g1.png'
    assert case['agent']['perceived'] == 'photo_like' and case['review'] is None
