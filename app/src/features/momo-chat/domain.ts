export const TRANSFER_KEYWORDS = ["chuyển tiền", "chuyen tien", "transfer", "chuyển", "chuyen"];
export const isTransferIntent = (s: string) =>
  TRANSFER_KEYWORDS.some((k) => s.toLowerCase().includes(k));

export const SUGGESTED_AMOUNTS = [50000, 100000, 200000, 500000, 1000000, 2000000];
export const formatVnd = (n: number) =>
  n.toLocaleString("vi-VN") + "₫";

export function parseAmount(text: string): number {
  const s = text.toLowerCase().replace(/\s+/g, " ");
  const m1 = s.match(/(\d+(?:[.,]\d+)?)\s*(k|m|tr|triệu|trieu|ngàn|ngan|nghìn|nghin)\b/);
  if (m1) {
    const n = parseFloat(m1[1].replace(",", "."));
    const u = m1[2];
    const mult =
      u === "k" || u.startsWith("ng") ? 1_000 :
      u === "m" || u === "tr" || u.startsWith("tri") ? 1_000_000 : 1;
    return Math.round(n * mult);
  }

  const m2 = s.match(/(\d[\d.,]{2,})/);
  if (m2) {
    const n = Number(m2[1].replace(/[.,]/g, ""));
    if (n >= 1000) return n;
  }
  return 0;
}

const CONTACTS: Record<string, string> = {
  "0901234567": "Nguyễn Văn An",
  "0912345678": "Trần Thị Bình",
  "0987654321": "Lê Minh Châu",
  "0978123456": "Phạm Quốc Dũng",
  "0934567890": "Hoàng Thu Hà",
};

const MOMO_USERS: Record<string, string> = {
  "0905111222": "Đặng Hoài Linh",
  "0966333444": "Vũ Khánh My",
  "0888555666": "Bùi Anh Tuấn",
  "0823777888": "Ngô Bảo Ngọc",
  "0772999000": "Cao Thành Đạt",
  "0356121314": "Đỗ Mai Phương",
  "0399151617": "Tạ Quang Huy",
  "0707181920": "Lý Hồng Nhung",
  "0902223344": "Nguyễn Hữu Phước",
  "0913445566": "Trần Quang Minh",
  "0988776655": "Lê Thị Hồng",
  "0977665544": "Phạm Văn Thắng",
  "0935112233": "Hoàng Anh Khoa",
  "0944556677": "Vũ Thị Lan",
  "0922334455": "Đào Quốc Bảo",
  "0967788990": "Trịnh Thu Trang",
  "0828112233": "Mai Đức Anh",
  "0793445566": "Phan Thị Yến",
  "0376778899": "Nguyễn Tuấn Kiệt",
  "0388990011": "Lương Thị Hằng",
  "0865443322": "Hồ Văn Sơn",
  "0796112334": "Đỗ Thanh Tùng",
  "0708994455": "Bùi Thị Hạnh",
  "0772334455": "Nguyễn Quỳnh Anh",
  "0918226677": "Tô Minh Quân",
  "0987001234": "Châu Bích Ngân",
  "0935667788": "Lâm Hữu Nghĩa",
  "0944112299": "Phùng Thị Diệu",
  "0926553311": "Đặng Văn Lộc",
  "0903556677": "Nguyễn Thị Kim Oanh",
  "0917889900": "Trần Minh Hiếu",
  "0964223344": "Vũ Phương Thảo",
  "0853223311": "Lê Hoàng Long",
  "0789445566": "Nguyễn Thị Mỹ Duyên",
  "0367445566": "Trương Văn Hùng",
  "0386778800": "Phạm Thị Thu Hằng",
  "0859223377": "Đoàn Quốc Việt",
  "0795332244": "Nguyễn Hoàng Nam",
  "0703887799": "Lê Thị Bích Vân",
  "0901002003": "Phan Minh Tâm",
  "0912004005": "Nguyễn Văn Trí",
  "0986007008": "Đặng Thu Hiền",
  "0976010011": "Trần Đăng Khoa",
  "0938013014": "Hồ Thị Thanh Mai",
  "0947016017": "Bùi Quang Vinh",
  "0928019020": "Đỗ Thị Ngọc Diệp",
  "0968022023": "Vũ Đình Phúc",
  "0824025026": "Nguyễn Lan Chi",
  "0792028029": "Phạm Hữu Lộc",
  "0378031032": "Lê Thị Tuyết Nhi",
  "0389034035": "Hoàng Văn Cường",
  "0866037038": "Trần Thị Diễm My",
  "0795040041": "Nguyễn Đức Thịnh",
  "0709043044": "Lý Thị Hồng Nhung",
  "0903046047": "Phan Quốc Anh",
  "0913049050": "Vương Thị Kiều Trinh",
  "0987052053": "Châu Văn Tiến",
  "0978055056": "Nguyễn Thị Phương Linh",
  "0934058059": "Đinh Hoàng Phi",
};

export type ContactLookup = {
  name: string;
  source: "contact" | "momo";
} | null;

export function parsePhone(text: string): string {
  const cleaned = text.replace(/[\s.\-()]/g, "");
  const m = cleaned.match(/0\d{8,10}/);
  return m ? m[0] : "";
}

export function lookupContact(phone: string): ContactLookup {
  if (!phone) return null;
  if (CONTACTS[phone]) return { name: CONTACTS[phone], source: "contact" };
  if (MOMO_USERS[phone]) return { name: MOMO_USERS[phone], source: "momo" };
  return null;
}

export type Person = { phone: string; name: string; source: "contact" | "momo" };

const ALL_PEOPLE: Person[] = [
  ...Object.entries(CONTACTS).map(
    ([phone, name]) => ({ phone, name, source: "contact" as const }),
  ),
  ...Object.entries(MOMO_USERS).map(
    ([phone, name]) => ({ phone, name, source: "momo" as const }),
  ),
];

function normalize(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d");
}

export function findByName(text: string): Person[] {
  const t = normalize(text);
  return ALL_PEOPLE.filter((p) => {
    const n = normalize(p.name);
    if (t.includes(n)) return true;
    const last = n.split(" ").pop() ?? "";
    if (last.length < 2) return false;
    return new RegExp(`\\b${last}\\b`).test(t);
  });
}

const LOOKUP_HINT = /\b(ai|la ai|sdt|so dien thoai|so dt|ten|thong tin|cua ai|nguoi nao)\b/;
export function isLookupQuery(text: string): boolean {
  const t = normalize(text);
  return LOOKUP_HINT.test(t) || t.trim().split(/\s+/).length <= 5;
}

export type TransferAction = {
  phone: string;
  name: string;
  source: "contact" | "momo";
  amount: number;
};

export type Message = {
  id: string;
  role: "user" | "bot";
  content: string;
  time: string;
  suggestions?: string[];
  transfer?: TransferAction;
};

export const API_URL = "http://127.0.0.1:8000/api/chat";
export const SESSION_KEY = "momo_chat_session_id";
