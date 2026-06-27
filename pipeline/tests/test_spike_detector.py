import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spike_detector import _select_candidates, detect_spikes


def _query(data):
    query = MagicMock()
    for method in ("select", "gte", "order", "limit"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=data)
    return query


def _database(feedback, alerts=None):
    db = MagicMock()
    feedback_query = _query(feedback)
    alert_query = _query(alerts or [])
    profile_query = _query([{"id": "user123"}])
    db.table.side_effect = lambda name: {
        "feedback": feedback_query,
        "alerts": alert_query,
        "profiles": profile_query,
    }[name]
    return db


class TestSpikeDetector(unittest.TestCase):
    def test_candidate_selection_prioritizes_department_coverage(self):
        candidates = [
            {"area": "A", "topic": "Safety", "team": "Vận hành"},
            {"area": "B", "topic": "Safety", "team": "Vận hành"},
            {"area": "C", "topic": "App Issue", "team": "IT"},
            {"area": "D", "topic": "Other", "team": "Sản phẩm"},
        ]

        selected = _select_candidates(candidates, recent_alerts=[], limit=3)

        self.assertEqual([group["team"] for group in selected], ["Vận hành", "IT", "Sản phẩm"])

    @patch("spike_detector.create_or_update_ticket")
    @patch("spike_detector.analyze_spike")
    @patch("spike_detector.get_supabase")
    @patch("spike_detector.has_supabase_admin_key", return_value=True)
    def test_overall_risk_drives_p5_override(
        self,
        _mock_has_key,
        mock_get_supabase,
        mock_analyze_spike,
        mock_create_ticket,
    ):
        mock_get_supabase.return_value = _database([{
            "id": "1",
            "text": "Rủi ro nghiêm trọng",
            "area": "HCM-Q1",
            "severity": "P2",
            "overall_risk": 5,
            "topic": "Pricing",
            "sentiment": "negative",
        }])
        mock_analyze_spike.return_value = {"title": "Rủi ro", "description": "Chi tiết", "action": "Xử lý"}
        mock_create_ticket.return_value = {"action": "created"}

        detect_spikes(max_spikes=1)

        self.assertEqual(mock_create_ticket.call_args.kwargs["team"], "Vận hành")
        self.assertEqual(mock_create_ticket.call_args.kwargs["severity"], "P5")

    @patch("spike_detector.get_supabase")
    @patch("spike_detector.has_supabase_admin_key", return_value=True)
    def test_no_spike_when_low_risk_counts_are_low(self, _mock_has_key, mock_get_supabase):
        mock_get_supabase.return_value = _database([
            {
                "id": "1",
                "text": "app chậm",
                "area": "HN-CauGiay",
                "severity": "P3",
                "topic": "App Issue",
                "sentiment": "negative",
            },
            {
                "id": "2",
                "text": "app lỗi",
                "area": "HN-CauGiay",
                "severity": "P3",
                "topic": "App Issue",
                "sentiment": "negative",
            },
        ])

        result = detect_spikes()

        self.assertEqual(result["spikes_detected"], 0)
        self.assertEqual(result["records_scanned"], 2)

    @patch("spike_detector.create_or_update_ticket")
    @patch("spike_detector.analyze_spike")
    @patch("spike_detector.get_supabase")
    @patch("spike_detector.has_supabase_admin_key", return_value=True)
    def test_p5_creates_immediate_incident_ticket(
        self,
        _mock_has_key,
        mock_get_supabase,
        mock_analyze_spike,
        mock_create_ticket,
    ):
        mock_get_supabase.return_value = _database([
            {
                "id": "1",
                "text": "Tai nạn, gọi 0912345678, xe 30A-12345",
                "area": "HCM-Q1",
                "severity": "P5",
                "topic": "Safety",
                "sentiment": "negative",
            }
        ])
        mock_analyze_spike.return_value = {
            "title": "Sự cố an toàn",
            "description": "Có tai nạn",
            "action": "Xác minh ngay",
        }
        mock_create_ticket.return_value = {"action": "created"}

        result = detect_spikes(max_spikes=1)

        self.assertEqual(result["alerts_created"], 1)
        kwargs = mock_create_ticket.call_args.kwargs
        self.assertEqual(kwargs["team"], "Vận hành")
        self.assertEqual(kwargs["topic"], "Safety")
        self.assertEqual(kwargs["ticket_type"], "incident")
        outbound_text = mock_analyze_spike.call_args.args[1][0]
        self.assertNotIn("0912345678", outbound_text)
        self.assertNotIn("30A-12345", outbound_text)

    @patch("spike_detector.create_or_update_ticket")
    @patch("spike_detector.analyze_spike")
    @patch("spike_detector.get_supabase")
    @patch("spike_detector.has_supabase_admin_key", return_value=True)
    def test_positive_cluster_creates_san_pham_opportunity(
        self,
        _mock_has_key,
        mock_get_supabase,
        mock_analyze_spike,
        mock_create_ticket,
    ):
        feedback = [
            {
                "id": str(index),
                "text": "Dịch vụ rất tốt",
                "area": "HN-CauGiay",
                "severity": "P1",
                "topic": "Other",
                "sentiment": "positive",
            }
            for index in range(5)
        ]
        mock_get_supabase.return_value = _database(feedback)
        mock_analyze_spike.return_value = {
            "title": "Tín hiệu tích cực",
            "description": "Khách hàng hài lòng",
            "action": "Khai thác truyền thông",
        }
        mock_create_ticket.return_value = {"action": "created"}

        result = detect_spikes(max_spikes=1)

        self.assertEqual(result["alerts_created"], 1)
        kwargs = mock_create_ticket.call_args.kwargs
        self.assertEqual(kwargs["team"], "Sản phẩm")
        self.assertEqual(kwargs["ticket_type"], "opportunity")

    @patch("spike_detector.create_or_update_ticket")
    @patch("spike_detector.analyze_spike")
    @patch("spike_detector.get_supabase")
    @patch("spike_detector.has_supabase_admin_key", return_value=True)
    def test_positive_app_issue_cluster_creates_san_pham_opportunity(
        self,
        _mock_has_key,
        mock_get_supabase,
        mock_analyze_spike,
        mock_create_ticket,
    ):
        # App Issue + positive nay route về Sản phẩm (góp ý UX) -> ticket opportunity.
        feedback = [
            {
                "id": str(index),
                "text": "Giao diện đặt xe rất mượt",
                "area": "HN-CauGiay",
                "severity": "P1",
                "topic": "App Issue",
                "sentiment": "positive",
            }
            for index in range(5)
        ]
        mock_get_supabase.return_value = _database(feedback)
        mock_analyze_spike.return_value = {
            "title": "Tín hiệu tích cực về app",
            "description": "Khách hàng khen giao diện",
            "action": "Khai thác cải tiến UX",
        }
        mock_create_ticket.return_value = {"action": "created"}

        result = detect_spikes(max_spikes=1)

        self.assertEqual(result["alerts_created"], 1)
        kwargs = mock_create_ticket.call_args.kwargs
        self.assertEqual(kwargs["team"], "Sản phẩm")
        self.assertEqual(kwargs["ticket_type"], "opportunity")


if __name__ == "__main__":
    unittest.main()
