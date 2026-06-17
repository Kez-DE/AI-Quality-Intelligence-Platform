import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spike_detector import detect_spikes

class TestSpikeDetector(unittest.TestCase):
    @patch("spike_detector.get_supabase")
    @patch("spike_detector.has_supabase_admin_key", return_value=True)
    def test_no_spike_when_counts_are_low(self, mock_has_key, mock_get_supabase):
        # Giả lập CSDL trả về ít phản hồi (dưới ngưỡng 5)
        mock_db = MagicMock()
        mock_db.table().select().gte().in_().order().limit().execute.return_value = MagicMock(
            data=[
                {"id": "1", "text": "test", "area": "HN-CauGiay", "severity": "P4", "topic": "Safety"},
                {"id": "2", "text": "test 2", "area": "HN-CauGiay", "severity": "P5", "topic": "Safety"},
            ]
        )
        mock_get_supabase.return_value = mock_db
        
        result = detect_spikes()
        self.assertEqual(result["spikes_detected"], 0)
        self.assertEqual(result["records_scanned"], 2)

    @patch("spike_detector.analyze_spike")
    @patch("spike_detector.get_supabase")
    @patch("spike_detector.has_supabase_admin_key", return_value=True)
    def test_spike_detected(self, mock_has_key, mock_get_supabase, mock_analyze_spike):
        # Giả lập CSDL trả về 5 phản hồi cùng một khu vực (vượt ngưỡng SPIKE_THRESHOLD=5)
        mock_db = MagicMock()
        
        # Tạo 5 bản ghi giả lập
        data = []
        for i in range(5):
            data.append({"id": str(i), "text": f"test {i}", "area": "HCM-Q1", "severity": "P5", "topic": "Safety"})
            
        mock_db.table().select().gte().in_().order().limit().execute.return_value = MagicMock(data=data)
        
        # Giả lập user id
        mock_db.table().select().limit().execute.return_value = MagicMock(data=[{"id": "user123"}])
        mock_get_supabase.return_value = mock_db
        
        # Giả lập LLM phân tích
        mock_analyze_spike.return_value = {
            "title": "Mock Spike Title",
            "description": "Mock Description",
            "action": "Mock Action",
            "assigned_team": "Safety"
        }
        
        result = detect_spikes(max_spikes=1)
        self.assertEqual(result["spikes_detected"], 1)
        self.assertEqual(result["records_scanned"], 5)
        self.assertEqual(result["alerts_created"], 1)

if __name__ == "__main__":
    unittest.main()
