"""P08-06 선행 얼굴 상태 주석: 소유자 확인 목록·병합 검증 규칙을 고정한다."""
import csv
import math
import random

import pytest

from scripts.p08_face_review import FIELDS, merge, owner_check_rows, read_counts


SETTINGS = dict(seed=20261013, annotations=dict(owner_random_fraction=0.2, output='face_review.csv'))


def write(path, fields, rows):
    with open(path, 'w', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(fields)
        writer.writerows(rows)


def test_owner_check_takes_all_flagged_and_seeded_ceil_fraction_of_rest():
    """검출 불일치·남은 얼굴 누락과 무작위 표본의 floor/전수 변경을 잡는다."""
    ids = [f'g{i:02d}' for i in range(13)]
    agent = {i: (1, 0) for i in ids}
    detected = {i: 1 for i in ids}
    agent['g00'] = (2, 0)     # 보임 수 ≠ 검출 수
    agent['g01'] = (1, 1)     # 검출 수는 같지만 얼굴이 남음
    detected['g02'] = 0       # 놓친 얼굴
    agent['g03'] = (0, 0); detected['g03'] = 0  # 얼굴 없음 일치는 flag 아님
    rows = owner_check_rows(ids, agent, detected, SETTINGS)
    flagged = [r['image_id'] for r in rows if r['reason'] == 'flagged']
    extra = [r['image_id'] for r in rows if r['reason'] == 'random']
    assert flagged == ['g00', 'g01', 'g02']
    rest = sorted(set(ids) - set(flagged))
    assert len(extra) == math.ceil(0.2 * len(rest)) == 2
    order = rest[:]
    random.Random(20261013).shuffle(order)
    assert extra == sorted(order[:2])
    # 나머지 11장: ceil 3, round·floor 2
    more = ids + ['g13']
    agent['g13'], detected['g13'] = (1, 0), 1
    assert sum(r['reason'] == 'random' for r in owner_check_rows(more, agent, detected, SETTINGS)) == 3


def test_read_counts_rejects_invalid_rows_and_accepts_boundaries(tmp_path):
    path = tmp_path / 'counts.csv'
    write(path, FIELDS, [('a', 0, 0), ('b', 2, 2)])
    assert read_counts(path, {'a', 'b'}) == {'a': (0, 0), 'b': (2, 2)}
    for rows, ids in [([('a', 1, 2)], {'a'}), ([('a', -1, 0)], {'a'}), ([('a', 1.5, 0)], {'a'}),
                      ([('a', '', 0)], {'a'}), ([('a', 1, 0), ('a', 1, 0)], {'a'}), ([('a', 1, 0)], {'a', 'b'})]:
        write(path, FIELDS, rows)
        with pytest.raises(ValueError):
            read_counts(path, ids)


def test_merge_prefers_owner_and_requires_complete_owner_check(tmp_path):
    """소유자 값이 에이전트 값을 덮고, 확인 목록 누락 시 최종 파일을 쓰지 않는다."""
    write(tmp_path / 'face_review_template.csv', FIELDS + ('confirmed',), [('a', '', '', ''), ('b', '', '', '')])
    write(tmp_path / 'face_review_agent.csv', FIELDS, [('a', 1, 0), ('b', 1, 0)])
    write(tmp_path / 'face_review_owner_check.csv', ('image_id', 'reason'), [('b', 'flagged')])
    settings = dict(SETTINGS, output_dir=str(tmp_path))
    write(tmp_path / 'face_review_owner.csv', FIELDS, [])
    with pytest.raises(ValueError):
        merge(settings)
    assert not (tmp_path / 'face_review.csv').exists()
    write(tmp_path / 'face_review_owner.csv', FIELDS, [('b', 2, 1)])
    merge(settings)
    assert (tmp_path / 'face_review.csv').read_text() == \
        'image_id,visible_faces,uncovered_visible_faces,confirmed\na,1,0,1\nb,2,1,1\n'
