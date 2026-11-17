"""
Script điều phối chạy crawl dữ liệu việc làm hàng ngày.
"""
import argparse
from crawlers.vietnamworks import run_daily_crawl as run_vietnamworks_crawl


def main():
    parser = argparse.ArgumentParser(description="Chạy crawl dữ liệu IT thị trường Việt Nam hàng ngày")
    parser.add_argument(
        "--site",
        choices=["vietnamworks", "all"],
        default="vietnamworks",
        help="Chọn trang cần cào dữ liệu (mặc định: vietnamworks)",
    )
    parser.add_argument("--pages", type=int, default=30, help="Số trang tối đa (mặc định 30)")
    parser.add_argument("--enrich-views", action="store_true", help="Cào thêm lượt xem/ứng tuyển")
    parser.add_argument("--date", type=str, default=None, help="Chỉ định ngày (YYYY-MM-DD)")
    parser.add_argument("--save-raw", action="store_true", help="Lưu dữ liệu JSON thô từng trang")
    parser.add_argument("--partial", action="store_true", help="Chế độ crawl 1 phần (không đánh dấu gone)")

    args = parser.parse_args()

    if args.site in ("vietnamworks", "all"):
        run_vietnamworks_crawl(
            max_pages=args.pages,
            enrich_views=args.enrich_views,
            target_date=args.date,
            save_raw=args.save_raw,
            is_partial=args.partial,
        )


if __name__ == "__main__":
    main()
