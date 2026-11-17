"""
Script thực thi cào dữ liệu ITviec hàng ngày:
1. Quét danh sách bài tuyển dụng (Step 1).
2. Cào chi tiết JD, Yêu cầu, Skills, Công ty (Step 2).
3. Chuẩn hóa và khử trùng lặp (Step 3).
4. Lưu Snapshot ngày và gộp vào file Master theo coalesce (Step 4).

Cách sử dụng:
    python crawlers/itviec/run.py
    python crawlers/itviec/run.py --pages 20
    python crawlers/itviec/run.py --no-headless
    python crawlers/itviec/run.py --test 5
"""
import argparse
import os
import sys
from datetime import date
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from crawlers.itviec.config import AUTH_FILE, MASTER_FILE, SNAPSHOT_DIR
from crawlers.itviec.spider import create_browser_context, crawl_job_cards, crawl_job_details
from crawlers.itviec.pipeline import deduplicate_jobs, update_master_and_snapshot


def main():
    parser = argparse.ArgumentParser(description="ITviec Daily Crawler")
    parser.add_argument("--pages", type=int, default=40, help="Số trang tối đa cần quét (mặc định 40)")
    parser.add_argument("--no-headless", action="store_true", help="Chạy browser hiển thị giao diện (mặc định headless)")
    parser.add_argument("--test", type=int, default=0, help="Chế độ thử nghiệm: chỉ cào N job chi tiết")
    args = parser.parse_args()

    today_iso = date.today().isoformat()
    print("=" * 70)
    print(f"BẮT ĐẦU CRAWL ITVIEC HÀNG NGÀY: {today_iso}")
    print("=" * 70)

    headless = not args.no_headless

    with sync_playwright() as p:
        browser, context = create_browser_context(p, headless=headless, auth_file=AUTH_FILE)
        page = context.new_page()

        # BƯỚC 1: Quét danh sách bài tuyển dụng
        cards = crawl_job_cards(page, max_pages=args.pages)
        if not cards:
            print("Không tìm thấy bài đăng nào. Dừng quy trình.")
            browser.close()
            return

        if args.test > 0:
            cards = cards[:args.test]
            print(f"*** CHẾ ĐỘ THỬ NGHIỆM: Chỉ cào {len(cards)} bài đăng chi tiết ***")

        # BƯỚC 2: Cào chi tiết JD và thông tin công ty
        full_jobs = crawl_job_details(page, cards)
        browser.close()

    # BƯỚC 3: Chuẩn hóa và xử lý trùng lặp
    df_clean = deduplicate_jobs(full_jobs)

    # BƯỚC 4: Lưu snapshot và gộp vào Master
    df_master = update_master_and_snapshot(df_clean, crawl_date=today_iso)

    print("\n" + "=" * 70)
    print("BÁO CÁO TỔNG KẾT ĐỢT CRAWL:")
    print("=" * 70)
    print(f"- Ngày thực hiện: {today_iso}")
    print(f"- Số bài cào được hôm nay: {len(df_clean)} tin")
    print(f"- Số tin có lương (has_salary): {int(df_clean['has_salary'].sum())} tin")
    print(f"- Số tin trùng lặp (is_duplicate): {int(df_clean['is_duplicate'].sum())} tin")
    print(f"- Tổng số việc làm tích lũy trong Master: {len(df_master)} tin")
    print("=" * 70)


if __name__ == "__main__":
    main()
