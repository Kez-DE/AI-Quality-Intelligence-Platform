import os, sys, unittest
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dispatch_utils import parse_deadline


class TestParseDeadline(unittest.TestCase):
    def _hours_from_now(self, dt: datetime) -> float:
        return (dt - datetime.now(timezone.utc)).total_seconds() / 3600

    def test_hours(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline("24h")), 24, delta=0.1)

    def test_days(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline("7d")), 168, delta=0.1)

    def test_weeks(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline("1w")), 168, delta=0.1)

    def test_none_defaults_48h(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline(None)), 48, delta=0.1)

    def test_garbage_defaults_48h(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline("ngay mai")), 48, delta=0.1)


if __name__ == "__main__":
    unittest.main()
