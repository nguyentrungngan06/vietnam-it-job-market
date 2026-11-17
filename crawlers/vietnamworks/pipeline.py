"""
Pipeline thu thập hàng ngày dữ liệu việc làm VietnamWorks.
Orchestrate: Search API Crawl -> Parse & Convert Salary -> (Tùy chọn: Views/Chi tiết) -> Update Master & Daily.
"""
import argparse
import json
from datetime import date
from pathlib import Path
import httpx
import pandas as pd

from .config import (
    DEFAULT_MAX_PAGES,
    RAW_DIR,
    SEARCH_HEADERS,
)
from .parsers import (
    add_salary_vnd,
    parse_detail_page,
    parse_job_item,
)
from .spider import (
    BlockedError,
    crawl_search_pages,
    fetch_detail_html,
)
from .tracker import update_master_and_daily


def run_daily_crawl(
    max_pages: int = DEFAULT_MAX_PAGES,
    enrich_views: bool = False,
    target_date: str | None = None,
    save_raw: bool = False,
    is_partial: bool = False,
) -> None:
    today_str = target_date or date.today().isoformat()
    print(f"=== BẮT ĐẦU CRAWL VIETNAMWORKS ({today_str}) ===")

    if save_raw:
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    raw_items = []
    total_pages_seen = 1
    pages_crawled = 0

    with httpx.Client(headers=SEARCH_HEADERS, timeout=30) as client:
        try:
            for page_num, total_pages, items in crawl_search_pages(client, max_pages=max_pages):
                total_pages_seen = total_pages
                pages_crawled += 1
                raw_items.extend(items)
                print(f"  [Trang {page_num}/{total_pages}] Lấy được {len(items)} tin")

                if save_raw:
                    raw_file = RAW_DIR / f"page_{page_num:03d}.json"
                    raw_file.write_text(
                        json.dumps({"data": items, "meta": {"nbPages": total_pages}}, ensure_ascii=False),
                        encoding="utf-8",
                    )
        except BlockedError as e:
            print(f"  [CẢNH BÁO] Dừng do bị chặn: {e}")
            is_partial = True

        if not raw_items:
            print("Không tìm thấy tin nào.")
            return

        print(f"\n-> Đã cào {len(raw_items)} tin từ {pages_crawled}/{total_pages_seen} trang.")

        # Bước 2: Parse và chuẩn hóa dữ liệu
        parsed_rows = [parse_job_item(j) for j in raw_items]
        df = pd.DataFrame(parsed_rows).drop_duplicates("job_id")
        df["site"] = "vietnamworks"
        df = add_salary_vnd(df)
        jobs_data = df.to_dict("records")

        # Bước 3 (Tùy chọn): Thu thập số lượt xem / ứng tuyển chi tiết
        if enrich_views:
            print("\n-> Đang lấy bổ sung lượt xem & hồ sơ ứng tuyển từ trang chi tiết...")
            for idx, job in enumerate(jobs_data, 1):
                url = job.get("url")
                if not url:
                    continue
                html = fetch_detail_html(client, url)
                if html:
                    details = parse_detail_page(html)
                    job["views"] = details.get("views", "")
                    job["applications"] = details.get("applications", "")
                    # Cập nhật thêm nếu mô tả bị cắt ngắn
                    if details.get("description") and len(details["description"]) > len(job.get("description", "")):
                        job["description"] = details["description"]
                    if details.get("requirement") and len(details["requirement"]) > len(job.get("requirement", "")):
                        job["requirement"] = details["requirement"]
                if idx % 50 == 0 or idx == len(jobs_data):
                    print(f"    Đã xử lý {idx}/{len(jobs_data)} tin chi tiết")

    # Bước 4: Cập nhật Master dataset và tạo Daily snapshot
    is_complete = (pages_crawled >= total_pages_seen) and not is_partial
    base_fields = list(df.columns)
    if "applications" not in base_fields and enrich_views:
        base_fields.append("applications")

    total_seen, new_count, gone_count = update_master_and_daily(
        current_jobs=jobs_data,
        base_fields=base_fields,
        today=today_str,
        is_complete_crawl=is_complete,
    )

    print("\n=== HOÀN THÀNH ===")
    print(f"  - Tổng tin thấy hôm nay: {total_seen}")
    print(f"  - Tin mới xuất hiện: {new_count}")
    print(f"  - Tin biến mất (gone): {gone_count}")
    print(f"  - Trạng thái hoàn thành: {'Đầy đủ (Complete)' if is_complete else 'Một phần (Partial)'}")


def main():
    parser = argparse.ArgumentParser(description="Crawler VietnamWorks hàng ngày")
    parser.add_argument("--pages", type=int, default=DEFAULT_MAX_PAGES, help="Số trang tối đa cần cào (mặc định 30)")
    parser.add_argument("--enrich-views", action="store_true", help="Cào thêm lượt xem/ứng tuyển từ trang chi tiết")
    parser.add_argument("--date", type=str, default=None, help="Chỉ định ngày crawl (YYYY-MM-DD)")
    parser.add_argument("--save-raw", action="store_true", help="Lưu lại file raw JSON từng trang")
    parser.add_argument("--partial", action="store_true", help="Chạy chế độ crawl một phần (không đánh dấu gone)")

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
