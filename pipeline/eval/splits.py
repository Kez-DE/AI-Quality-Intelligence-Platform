"""Deterministic train/holdout split of the golden set for honest eval.

The holdout is NEVER used to train any model — the routing accuracy gate
measures generalization on it, so the number is honest whether or not the
topic model was retrained.
"""
from __future__ import annotations
import random
from eval.route_eval import load_golden

SEED = 42
HOLDOUT_FRAC = 0.2


def golden_split(seed: int = SEED, holdout_frac: float = HOLDOUT_FRAC):
    data = list(load_golden())
    rng = random.Random(seed)
    rng.shuffle(data)
    cut = int(len(data) * (1 - holdout_frac))
    return data[:cut], data[cut:]   # (train, holdout)
