import unittest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from classifier import predict_feedback

class TestClassifier(unittest.TestCase):
    def test_safety_keyword_override(self):
        # "đánh nhau" là keyword an toàn, phải trả về severity P5 và topic Safety
        result = predict_feedback("Tài xế đánh nhau với khách hàng")
        self.assertEqual(result["severity"], "P5")
        self.assertEqual(result["topic"], "Safety")
        self.assertEqual(result["needs_review"], True)

    def test_positive_driver(self):
        # Câu khen tài xế
        result = predict_feedback("Bác tài xế thân thiện, xe sạch sẽ")
        self.assertEqual(result["sentiment"], "positive")
        self.assertTrue(result["severity"] in ["P1", "P2"])

    def test_negative_general(self):
        # Câu chê tệ
        result = predict_feedback("Dịch vụ quá tệ, không bao giờ dùng lại")
        self.assertEqual(result["sentiment"], "negative")

    def test_negation_guard(self):
        # Mặc dù có chữ "tệ" nhưng có phủ định "không" ngay trước
        result = predict_feedback("Chất lượng không tệ như mọi người nói, mình thấy ổn")
        self.assertNotEqual(result["sentiment"], "negative", "Nên xử lý từ phủ định để không bị nhận nhầm là tiêu cực")

if __name__ == "__main__":
    unittest.main()
