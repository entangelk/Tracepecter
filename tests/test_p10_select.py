"""P10-01 selection of unreviewed cross-boundary candidates.

Under-strict guards: a cross-split pair just above a band edge, a GEN pair touching
test_unseen and an unsampled lower band must all be selected or counted.
Over-strict guards: same-split, already reviewed and cross-class pairs are excluded,
and samples never exceed the band size or depend on input order.
"""
import random

import pytest

from scripts import p10_select


SPLITS = dict(r1='train', r2='val', r3='train', r4='test', g1='train', g2='test_unseen', g3='val')
LABELS = dict(r1='1', r2='1', r3='1', r4='1', g1='0', g2='0', g3='0')


def pair(a, b, cosine):
    return dict(a=a, b=b, cosine=str(cosine), phash_distance='20', reasons='embedding_topk')


def test_cross_boundary_pairs_are_selected_by_band():
    candidates = [pair('r1', 'r2', 0.90), pair('r1', 'r4', 0.8999), pair('g1', 'g2', 0.95), pair('g1', 'g3', 0.5)]
    selected, population = p10_select.select_pairs(candidates, SPLITS, LABELS, set())
    by_pair = {(r['a'], r['b']): r['stratum'] for r in selected}
    assert by_pair == {('r1', 'r2'): 'real_ge90', ('r1', 'r4'): 'real_85_90', ('g1', 'g2'): 'gen_ge95'}
    # GEN below .90 is counted as an unreviewed band, not silently dropped.
    assert population['gen_lt90'] == 1


def test_same_split_reviewed_and_cross_class_pairs_are_excluded():
    candidates = [pair('r1', 'r3', 0.99), pair('r2', 'r1', 0.95), pair('r1', 'g3', 0.99)]
    selected, population = p10_select.select_pairs(candidates, SPLITS, LABELS, {('r1', 'r2')})
    assert selected == [] and sum(population.values()) == 0


def test_sample_is_bounded_and_independent_of_input_order():
    ids = [f'x{i:03}' for i in range(300)]
    splits = {i: ('train' if n % 2 else 'val') for n, i in enumerate(ids)}
    labels = dict.fromkeys(ids, '1')
    candidates = [pair(ids[n], ids[n+1], 0.70 + n/10000) for n in range(299)]
    first, population = p10_select.select_pairs(candidates, splits, labels, set())
    shuffled = candidates[:]
    random.Random(1).shuffle(shuffled)
    second, _ = p10_select.select_pairs(shuffled, splits, labels, set())
    assert population['real_lt80'] == 299 and len(first) == 100 and first == second
    other_seed, _ = p10_select.select_pairs(candidates, splits, labels, set(), seed=1)
    assert other_seed != first


def test_small_band_is_taken_in_full():
    selected, _ = p10_select.select_pairs([pair('r1', 'r2', 0.70)], SPLITS, LABELS, set())
    assert [r['stratum'] for r in selected] == ['real_lt80']


@pytest.mark.skipif(not p10_select.QUEUE.is_file(), reason='untracked P09 candidate queue is absent')
def test_tampered_input_is_rejected(tmp_path, monkeypatch):
    p10_select.verify_inputs()
    copy = tmp_path/'metadata.csv'
    copy.write_bytes(p10_select.METADATA.read_bytes() + b'\n')
    monkeypatch.setattr(p10_select, 'METADATA', copy)
    with pytest.raises(ValueError, match='hash mismatch'):
        p10_select.verify_inputs()
