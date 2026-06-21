"""Khóa hành vi của Waterfall risk-scoring.

Bất biến quan trọng: P5 (overall_risk == 5) ⟹ routing ép về team Safety.
Vì vậy CHỈ rủi ro an toàn tính mạng mới được lên P5 — gian lận (fraud), dù
nghiêm trọng, tối đa P4 để không bị định tuyến nhầm sang Safety.
"""

from agents.scoring_agent import calculate_overall_risk


def _risk(safety=0, fraud=0, attitude=0, vehicle=0, compliance=0):
    return calculate_overall_risk(safety, fraud, attitude, vehicle, compliance)


def test_only_safety_reaches_p5():
    assert _risk(safety=8) == 5
    assert _risk(safety=10) == 5


def test_fraud_caps_at_p4_not_p5():
    # Gian lận nặng KHÔNG được lên P5 (tránh ép nhầm sang team Safety).
    assert _risk(fraud=8) == 4
    assert _risk(fraud=10) == 4


def test_severe_attitude_caps_at_p4():
    assert _risk(attitude=8) == 4
    assert _risk(attitude=10) == 4


def test_mid_level_risks():
    assert _risk(safety=5) == 4
    assert _risk(fraud=5) == 4
    assert _risk(vehicle=6) == 3
    assert _risk(compliance=6) == 3


def test_low_and_baseline():
    assert _risk(attitude=3) == 2
    assert _risk() == 1
