"""Tiện ích PostgREST dùng chung.

PostgREST cap cứng số dòng mỗi response (project này = 1000). `.limit(N>1000)` vẫn chỉ
trả 1000 → quét thiếu data (spike_detector, SLA...). `fetch_paginated` lặp `.range()` để
lấy vượt cap.
"""
from __future__ import annotations

from typing import Callable

PAGE_SIZE = 1000  # = db-max-rows của PostgREST project


def fetch_paginated(make_query: Callable, cap: int | None = None, page_size: int = PAGE_SIZE) -> list:
    """Lấy toàn bộ (hoặc tới `cap`) dòng, vượt cap 1000/response.

    make_query(): trả về MỘT query builder MỚI (đã .select()/.eq()/.order(), CHƯA .range()/.execute()).
    Phải tạo builder mới mỗi lần gọi (builder có state, không tái dùng qua các trang).
    """
    rows: list = []
    offset = 0
    while True:
        want = page_size if cap is None else min(page_size, cap - len(rows))
        if want <= 0:
            break
        page = make_query().range(offset, offset + want - 1).execute().data or []
        rows.extend(page)
        if len(page) < want:      # hết data
            break
        offset += len(page)
    return rows
