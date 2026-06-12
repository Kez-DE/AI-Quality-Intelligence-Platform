// Region mapping thống nhất cho frontend. Mirror của pipeline/regions.py.
// DB lưu CODE (vd 'HN-Cau-Giay'); UI luôn hiển thị LABEL ('Cầu Giấy, Hà Nội').

export const REGIONS: { code: string; label: string }[] = [
  { code: "HN-Cau-Giay", label: "Cầu Giấy, Hà Nội" },
  { code: "HN-Ha-Dong", label: "Hà Đông, Hà Nội" },
  { code: "HN-Dong-Da", label: "Đống Đa, Hà Nội" },
  { code: "HN-Hoan-Kiem", label: "Hoàn Kiếm, Hà Nội" },
  { code: "HN-Tay-Ho", label: "Tây Hồ, Hà Nội" },
  { code: "HN-Long-Bien", label: "Long Biên, Hà Nội" },
  { code: "HCM-Quan-1", label: "Quận 1, Hồ Chí Minh" },
  { code: "HCM-Binh-Thanh", label: "Bình Thạnh, Hồ Chí Minh" },
  { code: "HCM-Thu-Duc", label: "Thủ Đức, Hồ Chí Minh" },
  { code: "HCM-Quan-7", label: "Quận 7, Hồ Chí Minh" },
  { code: "HCM-Tan-Binh", label: "Tân Bình, Hồ Chí Minh" },
  { code: "HCM-Go-Vap", label: "Gò Vấp, Hồ Chí Minh" },
  { code: "DN-Hai-Chau", label: "Hải Châu, Đà Nẵng" },
  { code: "DN-Son-Tra", label: "Sơn Trà, Đà Nẵng" },
  { code: "DN-Ngu-Hanh-Son", label: "Ngũ Hành Sơn, Đà Nẵng" },
  { code: "DN-Thanh-Khe", label: "Thanh Khê, Đà Nẵng" },
];

const CODE_TO_LABEL: Record<string, string> = Object.fromEntries(
  REGIONS.map((r) => [r.code, r.label]),
);
const LABEL_TO_LABEL: Record<string, string> = Object.fromEntries(
  REGIONS.map((r) => [r.label.toLowerCase(), r.label]),
);

// Alias: form dropdown dùng tên AREAS.
export const AREAS = REGIONS;

// Luôn trả label đẹp từ code HOẶC label. Dùng ở mọi nơi hiển thị khu vực.
export function regionLabel(codeOrLabel: string | null | undefined): string {
  if (!codeOrLabel) return "Không rõ";
  if (CODE_TO_LABEL[codeOrLabel]) return CODE_TO_LABEL[codeOrLabel];
  if (LABEL_TO_LABEL[codeOrLabel.toLowerCase()]) return codeOrLabel;
  return codeOrLabel;
}
