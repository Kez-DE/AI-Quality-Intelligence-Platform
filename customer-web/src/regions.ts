// Copied from app/src/lib/regions.ts, itself a hand-kept mirror of
// pipeline/regions.py. The backend stores the CODE; the UI shows the LABEL.
// Keep all three in sync when an area is added.

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

/** Areas grouped by city (the label's last part), in list order, for <optgroup>. */
export const AREA_GROUPS: { city: string; areas: typeof REGIONS }[] = [];
for (const region of REGIONS) {
  const city = region.label.split(", ").pop() ?? region.label;
  const group = AREA_GROUPS.find((g) => g.city === city);
  if (group) group.areas.push(region);
  else AREA_GROUPS.push({ city, areas: [region] });
}
