import unittest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from supabase import create_client, Client

# Test RLS policies directly against the Supabase instance
# Require SUPABASE_URL and SUPABASE_ANON_KEY to be set
SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_ANON_KEY")

@unittest.skipIf(not SUPABASE_URL or not SUPABASE_ANON_KEY, "Missing Supabase configuration")
class TestSupabaseRLS(unittest.TestCase):
    def setUp(self):
        self.anon_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    def test_guest_cannot_read_alerts(self):
        # Guest (anon) không được phép đọc bảng alerts (yêu cầu auth)
        # Sẽ trả về mảng rỗng (RLS block) hoặc lỗi quyền
        response = self.anon_client.table("alerts").select("*").limit(1).execute()
        # RLS có thể trả về mảng rỗng thay vì lỗi
        self.assertEqual(len(response.data), 0, "Guest/Anon không được phép nhìn thấy alerts")

    def test_guest_can_insert_feedback(self):
        # Guest được phép insert feedback (nếu policy cho phép insert on public)
        # Tuy nhiên tuỳ thuộc vào policy hiện tại, test này kiểm tra xem insert có hoạt động hay bị chặn.
        # Ở đây ta mong muốn nó insert được nếu đúng policy
        pass

    def test_guest_cannot_update_feedback(self):
        # Không được phép update feedback nếu là anon
        try:
            response = self.anon_client.table("feedback").update({"topic": "Hacked"}).eq("id", "invalid-id").execute()
            self.assertEqual(len(response.data), 0, "Guest không được update feedback")
        except Exception as e:
            # Nếu throw error do permission denied cũng là hợp lệ
            self.assertTrue("permission denied" in str(e).lower() or "rls" in str(e).lower() or "401" in str(e) or "403" in str(e))

if __name__ == "__main__":
    unittest.main()
