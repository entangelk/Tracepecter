"""P08 사전등록 판정 계산. 입력 확률·주석에서 보고서를 유도하며 fitting하지 않는다."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np


def wilson(events, count, confidence=.95):
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    p = events / count
    denominator = 1 + z*z/count
    center = (p + z*z/(2*count)) / denominator
    half = z * math.sqrt(p*(1-p)/count + z*z/(4*count*count)) / denominator
    return [max(0., center-half), min(1., center+half)]


def newcombe(events1, count1, events2, count2, confidence=.95):
    p1, p2 = events1/count1, events2/count2
    l1, u1 = wilson(events1, count1, confidence)
    l2, u2 = wilson(events2, count2, confidence)
    return [max(-1., p1-p2-math.hypot(p1-l1, u2-p2)),
            min(1., p1-p2+math.hypot(u1-p1, p2-l2))]


def intervention(ids, reference, variant, labels, threshold, settings):
    rules = settings['intervention_rules']
    ids = sorted(ids)
    n = len(ids)
    if (n < rules['min_images'] or n != len(set(ids))
            or any(i not in reference or i not in variant or i not in labels for i in ids)):
        return dict(status='indeterminate', count=n, reason='missing_duplicate_or_insufficient')
    ref = np.asarray([reference[i] for i in ids], dtype=float)
    var = np.asarray([variant[i] for i in ids], dtype=float)
    y = np.asarray([labels[i] for i in ids])
    if (not np.all(np.isfinite(ref)) or not np.all(np.isfinite(var))
            or not np.all((ref >= 0) & (ref <= 1) & (var >= 0) & (var <= 1))
            or not np.all(np.isin(y, [0, 1]))):
        return dict(status='indeterminate', count=n, reason='invalid_predictions_or_labels')
    signed = (var-ref)*100
    absolute = np.abs(signed)
    score_rules, error_rules = rules['score'], rules['error']
    rng = np.random.Generator(np.random.PCG64(settings['seed']))
    indices = rng.integers(0, n, size=(score_rules['resamples'], n))
    tail = round((1-score_rules['confidence'])*50, 12)
    interval = np.percentile(absolute[indices].mean(axis=1), [tail, 100-tail], method='linear')
    correct_ref, correct_var = (ref >= threshold) == y, (var >= threshold) == y
    harmful = int((correct_ref & ~correct_var).sum())
    reverse = int((~correct_ref & correct_var).sum())
    error_ci = wilson(harmful, n, error_rules['confidence'])
    passed = interval[1] <= score_rules['max_upper'] and error_ci[1] <= error_rules['max_upper']
    return dict(status='pass' if passed else 'fail', count=n,
                mean_signed_shift=float(signed.mean()), mean_absolute_shift=float(absolute.mean()),
                absolute_shift_ci=interval.tolist(), correct_to_wrong=harmful,
                wrong_to_correct=reverse, error_risk=harmful/n, error_ci=error_ci,
                signed_shift_quantiles=np.percentile(signed, [0, 25, 50, 75, 100]).tolist())


def concentration(annotations, probabilities, generators, threshold, settings):
    rules = settings['face_concentration']
    groups = {s: [] for s in rules['states']}
    if any(i not in probabilities or i not in generators for i in annotations):
        return dict(status='indeterminate', reason='missing_prediction_or_generator')
    for image_id, (visible, uncovered) in annotations.items():
        p = probabilities[image_id]
        if (type(visible) is not int or type(uncovered) is not int or not 0 <= uncovered <= visible
                or not math.isfinite(p) or not 0 <= p <= 1):
            return dict(status='indeterminate', reason='invalid_annotation_or_prediction')
        state = 'missed_visible_face' if uncovered else 'no_visible_face' if visible == 0 else 'anonymized'
        groups[state].append(image_id)
    def summary(ids):
        n = len(ids)
        events = sum(probabilities[i] >= threshold for i in ids)
        return dict(count=n, false_positives=events, rate=events/n if n else None,
                    ci=wilson(events, n, rules['confidence']) if n else None)
    states = {s: summary(ids) for s, ids in groups.items()}
    by_generator = {g: {s: summary([i for i in ids if generators[i] == g]) for s, ids in groups.items()}
                    for g in sorted({generators[i] for i in annotations})}
    if any(v['count'] < rules['min_images_per_state'] for v in states.values()):
        return dict(status='indeterminate', states=states, generators=by_generator,
                    reason='missing_or_insufficient_state')
    comparisons = []
    for s1, s2 in rules['comparisons']:
        a, b = states[s1], states[s2]
        interval = newcombe(a['false_positives'], a['count'], b['false_positives'], b['count'], rules['confidence'])
        limit = rules['max_absolute_rate_difference']
        comparisons.append(dict(states=[s1, s2], difference=a['rate']-b['rate'], ci=interval,
                                status='pass' if interval[0] >= -limit and interval[1] <= limit else 'fail'))
    return dict(status='pass' if all(c['status'] == 'pass' for c in comparisons) else 'fail',
                states=states, generators=by_generator, comparisons=comparisons)


def adoption(standard_auc, unseen_auc, gates, settings):
    rules = settings['adoption']
    aucs = [standard_auc, unseen_auc]
    auc_pass = (all(v is not None and math.isfinite(v) for v in aucs)
                and standard_auc >= rules['standard_anonymized_roc_auc_min']
                and unseen_auc >= rules['unseen_anonymized_roc_auc_min'])
    cue_pass = all(gates.get(k, {}).get('status') == 'pass' for k in rules['required_cue_gates'])
    return dict(adopt=bool(auc_pass and cue_pass), auc_pass=bool(auc_pass), cues_pass=cue_pass,
                standard_auc=standard_auc, unseen_auc=unseen_auc,
                action=rules['pass'] if auc_pass and cue_pass else rules['non_adoption'])
