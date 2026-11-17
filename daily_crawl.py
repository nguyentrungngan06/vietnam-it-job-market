"""
Script điều phối chạy crawl dữ liệu việc làm và thị trường IT Việt Nam hàng ngày.
"""
import argparse
from crawlers.vietnamworks import run_daily_crawl as run_vietnamworks_crawl
from crawlers.github import run_github_crawl


def main():
    parser = argparse.ArgumentParser(description="Chạy crawl dữ liệu IT thị trường Việt Nam hàng ngày")
    parser.add_argument(
        "--site",
        choices=["vietnamworks", "github", "all"],
        default="vietnamworks",
        help="Chọn nguồn cần cào dữ liệu (mặc định: vietnamworks)",
    )

    # Tùy chọn cho VietnamWorks
    parser.add_argument("--pages", type=int, default=30, help="Số trang tối đa VietnamWorks (mặc định 30)")
    parser.add_argument("--enrich-views", action="store_true", help="Cào thêm lượt xem/ứng tuyển (VietnamWorks)")
    parser.add_argument("--date", type=str, default=None, help="Chỉ định ngày (YYYY-MM-DD)")
    parser.add_argument("--save-raw", action="store_true", help="Lưu dữ liệu JSON thô từng trang")
    parser.add_argument("--partial", action="store_true", help="Chế độ crawl 1 phần (không đánh dấu gone)")

    # Tùy chọn cho GitHub Skills
    parser.add_argument("--github-token", type=str, default=None, help="GitHub Personal Access Token")
    parser.add_argument("--users-per-city", type=int, default=100, help="Số users tối đa quét mỗi tỉnh (GitHub)")
    parser.add_argument("--min-users", type=int, default=5, help="Ngưỡng tối thiểu hồ sơ để xử lý tỉnh (GitHub)")

    args = parser.parse_args()

    if args.site in ("vietnamworks", "all"):
        run_vietnamworks_crawl(
            max_pages=args.pages,
            enrich_views=args.enrich_views,
            target_date=args.date,
            save_raw=args.save_raw,
            is_partial=args.partial,
        )

    if args.site in ("github", "all"):
        run_github_crawl(
            token=args.github_token,
            sample_users_per_city=args.users_per_city,
            min_users_threshold=args.min_users,
            target_date=args.date,
        )


if __name__ == "__main__":
    main()
