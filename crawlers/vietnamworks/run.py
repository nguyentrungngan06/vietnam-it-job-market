"""
Script thực thi cào dữ liệu VietnamWorks hàng ngày:
1. Quét danh sách bài tuyển dụng qua REST API (ngành CNTT/VT).
2. Chuẩn hóa bảng dữ liệu và quy đổi lương về triệu VND/tháng (lưu data/out/vietnamworks.csv).
3. (Tùy chọn --enrich-views): Cào lượt xem, ứng tuyển và full text chi tiết từ trang tuyển dụng.
4. Cập nhật vòng đời tin vào Master và tạo file Daily snapshot (data/daily/).

Cách sử dụng:
    # 1. Chế độ crawl nhanh (mặc định: ~1 phút)
    python crawlers/vietnamworks/run.py

    # 2. Chế độ crawl đầy đủ (kèm views, ứng tuyển & full text: ~25 phút)
    python crawlers/vietnamworks/run.py --enrich-views

    # 3. Các tùy chọn khác
    python crawlers/vietnamworks/run.py --pages 20
    python crawlers/vietnamworks/run.py --date 2026-11-19
"""
import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from crawlers.vietnamworks.config import DEFAULT_MAX_PAGES
from crawlers.vietnamworks.pipeline import run_daily_crawl


def main():
    parser = argparse.ArgumentParser(description="VietnamWorks Daily Crawler")
    parser.add_argument("--pages", type=int, default=DEFAULT_MAX_PAGES, help="Số trang tối đa cần quét (mặc định 30)")
    parser.add_argument("--enrich-views", action="store_true", help="Cào thêm lượt xem, ứng tuyển và full text chi tiết")
    parser.add_argument("--date", type=str, default=None, help="Chỉ định ngày crawl (YYYY-MM-DD)")
    parser.add_argument("--save-raw", action="store_true", help="Lưu lại file raw JSON từng trang")
    parser.add_argument("--partial", action="store_true", help="Chế độ crawl dở dang (không đánh dấu gone cho tin cũ)")

    args = parser.parse_args()

    run_daily_crawl(
        max_pages=args.pages,
        enrich_views=args.enrich_views,
        target_date=args.date,
        save_raw=args.save_raw,
        is_partial=args.partial,
    )


if __name__ == "__main__":
    main()
