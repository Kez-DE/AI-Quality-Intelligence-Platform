import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException

from auth_guard import AuthUser, can_view_team, scoped_team


def _user(role: str, department=None) -> AuthUser:
    return AuthUser(id="u1", email="u@x.com", role=role, department=department)


class TestCanViewTeam(unittest.TestCase):
    def test_admin_sees_any_team(self):
        admin = _user("admin")
        self.assertTrue(can_view_team(admin, "Vận hành"))
        self.assertTrue(can_view_team(admin, "IT"))
        self.assertTrue(can_view_team(admin, None))

    def test_ops_sees_only_own_team(self):
        mgr = _user("manager", "Vận hành")
        self.assertTrue(can_view_team(mgr, "Vận hành"))
        self.assertFalse(can_view_team(mgr, "IT"))

    def test_staff_sees_only_own_team(self):
        staff = _user("staff", "CSKH")
        self.assertTrue(can_view_team(staff, "CSKH"))
        self.assertFalse(can_view_team(staff, "IT"))

    def test_unassigned_ops_sees_nothing(self):
        mgr = _user("manager", None)
        self.assertFalse(can_view_team(mgr, "Vận hành"))
        self.assertFalse(can_view_team(mgr, None))


class TestScopedTeam(unittest.TestCase):
    def test_admin_respects_requested_team(self):
        admin = _user("admin")
        self.assertEqual(scoped_team(admin, "IT"), "IT")
        self.assertIsNone(scoped_team(admin, None))  # None = xem tất cả

    def test_ops_forced_to_own_team(self):
        mgr = _user("manager", "Vận hành")
        # Dù xin team khác vẫn bị ép về phòng của mình
        self.assertEqual(scoped_team(mgr, "IT"), "Vận hành")
        self.assertEqual(scoped_team(mgr, None), "Vận hành")

    def test_unassigned_ops_raises_403(self):
        mgr = _user("manager", None)
        with self.assertRaises(HTTPException) as ctx:
            scoped_team(mgr, None)
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
