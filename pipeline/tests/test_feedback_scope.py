from main import _feedback_team


def test_feedback_scope_uses_topic_and_sentiment_routing():
    assert _feedback_team({"topic": "App Issue", "severity": "P3", "sentiment": "negative"}) == "IT"
    assert _feedback_team({"topic": "Other", "severity": "P1", "sentiment": "positive"}) == "Marketing"


def test_feedback_scope_uses_overall_risk_for_p5_override():
    feedback = {
        "topic": "Pricing",
        "severity": "P2",
        "overall_risk": 5,
        "sentiment": "negative",
    }
    # overall_risk=5 -> P5 override -> Vận hành (đội phản ứng nhanh), không còn về Safety.
    assert _feedback_team(feedback) == "Vận hành"
