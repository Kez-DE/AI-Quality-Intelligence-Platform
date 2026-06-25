import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from eval.route_eval import load_golden, evaluate

TARGET_DEPT_ACCURACY = 0.80
MAX_SINGLE_MISROUTE = 150          # không ô (gold->pred) sai nào vượt mức này
MAX_WORKLOAD_SKEW = 0.35           # |tải_thực - tải_đúng| / tải_đúng <= 35%


class TestRoutingAccuracy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = evaluate(load_golden())

    def test_department_accuracy_meets_target(self):
        self.assertGreaterEqual(
            self.r["dept_accuracy"], TARGET_DEPT_ACCURACY,
            f"dept accuracy {self.r['dept_accuracy']:.3f} < {TARGET_DEPT_ACCURACY}",
        )

    def test_no_single_misroute_too_large(self):
        worst = [
            (g, p, c)
            for (g, p), c in self.r["dept_confusion"].items()
            if g != p and c > MAX_SINGLE_MISROUTE
        ]
        self.assertEqual(worst, [], f"Ô misroute quá lớn: {worst}")

    def test_workload_not_skewed(self):
        gold = self.r["gold_dept_dist"]
        pred = self.r["pred_dept_dist"]
        skewed = []
        for dept, g in gold.items():
            p = pred.get(dept, 0)
            if g and abs(p - g) / g > MAX_WORKLOAD_SKEW:
                skewed.append((dept, g, p))
        self.assertEqual(skewed, [], f"Tải lệch >35%: {skewed}")


if __name__ == "__main__":
    unittest.main()
