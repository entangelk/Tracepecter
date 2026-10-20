"""Final P09 groups preserve visual verdicts and conservative allocation separately."""
import pytest

from scripts.p09_finalize_groups import prepare_groups


def test_uncertain_pair_is_colocated_without_becoming_a_confirmed_visual_match():
    """Under: keep reviewed uncertainty together; over: never upgrade its visual verdict."""
    rows = [dict(image_id=i, label='1', look_group='', source_domain='kfashion', generator='') for i in ('a', 'b', 'c')]
    reviews = [dict(a='a', b='b', verdict='unconfirmed', reason='ambiguous original')]
    groups, constraints = prepare_groups(rows, reviews)
    assert groups['a'] == groups['b'] != groups['c']
    assert reviews[0]['verdict'] == 'unconfirmed'
    assert constraints[0]['verdict'] == 'conservative_colocation'


def test_unseen_generator_conflict_is_rejected_but_same_generator_group_is_allowed():
    """Under: reject a holdout-crossing group; over: allow reviewed within-generator groups."""
    rows = [dict(image_id=i, label='0', look_group='', source_domain='', generator=g)
            for i, g in [('a', 'sd35_medium'), ('b', 'sd35_medium')]]
    reviews = [dict(a='a', b='b', verdict='confirmed_same_look', reason='visual')]
    assert len(set(prepare_groups(rows, reviews)[0].values())) == 1
    rows[1]['generator'] = 'z_image_turbo'
    with pytest.raises(ValueError, match='unseen generator'):
        prepare_groups(rows, reviews)
