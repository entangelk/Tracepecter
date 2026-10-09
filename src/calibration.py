"""P05 calibration 수치 계약: temperature/threshold/score (provider 독립)."""
from __future__ import annotations

import math
import numpy as np


def apply_temperature(logits, temperature: float) -> np.ndarray:
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError('temperature must be finite and positive')
    scaled = np.asarray(logits, dtype=float) / temperature
    return np.exp(-np.logaddexp(0, -scaled))


def _prediction_arrays(values, labels):
    values, labels = np.asarray(values, dtype=float), np.asarray(labels, dtype=float)
    if values.ndim != 1 or values.shape != labels.shape or not np.all(np.isfinite(values)):
        raise ValueError('finite aligned one-dimensional predictions required')
    if not len(labels) or not np.all(np.isin(labels, [0, 1])):
        raise ValueError('nonempty binary labels required')
    return values, labels


def _nll(logits, labels, temperature):
    scaled = logits / temperature
    return float(np.mean(np.logaddexp(0, scaled) - labels * scaled))


def fit_temperature(logits, labels, minimum: float, maximum: float, iterations: int) -> float:
    logits, labels = _prediction_arrays(logits, labels)
    if np.unique(labels).size != 2:
        raise ValueError('validation fitting requires both binary classes')
    if not (math.isfinite(minimum) and math.isfinite(maximum) and 0 < minimum <= 1 <= maximum) or iterations < 1:
        raise ValueError('temperature bounds must contain 1; iterations must be positive')
    left, right = math.log(minimum), math.log(maximum)
    ratio = (math.sqrt(5) - 1) / 2
    c, d = right - ratio * (right-left), left + ratio * (right-left)
    fc, fd = _nll(logits, labels, math.exp(c)), _nll(logits, labels, math.exp(d))
    for _ in range(iterations):
        if fc < fd:
            right, d, fd = d, c, fc
            c = right - ratio * (right-left)
            fc = _nll(logits, labels, math.exp(c))
        else:
            left, c, fc = c, d, fd
            d = left + ratio * (right-left)
            fd = _nll(logits, labels, math.exp(d))
    candidates = [1.0, minimum, maximum, math.exp((left+right)/2)]
    return min(candidates, key=lambda t: _nll(logits, labels, t))


def choose_threshold(labels, probabilities) -> float:
    probabilities, labels = _prediction_arrays(probabilities, labels)
    if np.unique(labels).size != 2:
        raise ValueError('threshold fitting requires both binary classes')
    if np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError('probabilities must be within [0,1]')
    def key(threshold):
        predicted = probabilities >= threshold
        balanced = ((predicted[labels == 1]).mean() + (~predicted[labels == 0]).mean()) / 2
        return (-balanced, abs(threshold-0.5), threshold)
    return float(min(np.unique(np.r_[0.0, probabilities, 0.5, 1.0]), key=key))


def calibration_metrics(logits, labels, temperature: float, bins: int) -> dict:
    logits, labels = _prediction_arrays(logits, labels)
    if bins < 1:
        raise ValueError('ECE bins must be positive')
    probabilities = apply_temperature(logits, temperature)
    assignments = np.minimum((probabilities * bins).astype(int), bins-1)
    ece = 0.0
    for index in range(bins):
        mask = assignments == index
        if mask.any():
            ece += float(mask.mean() * abs(probabilities[mask].mean() - labels[mask].mean()))
    return dict(nll=_nll(logits, labels, temperature),
                brier=float(np.mean((probabilities-labels)**2)), ece=ece)
