"""
Pipeline điều phối quét và phân tích kỹ năng lập trình viên theo tỉnh thành trên GitHub.
Tự động xuất dữ liệu thống kê ra thư mục data/daily/.
"""
from datetime import date
from collections import Counter
from pathlib import Path
import httpx
import pandas as pd

from .config import (
    DAILY_DIR,
    DEFAULT_SAMPLE_USERS_PER_CITY,
    DEFAULT_MIN_USERS_THRESHOLD,
    LOCATION_QUERIES,
    resolve_github_token,
)
from .spider import (
    get_headers,
    search_users_in_location,
    extract_user_skills,
)


def run_github_crawl(
    token: str | None = None,
    sample_users_per_city: int = DEFAULT_SAMPLE_USERS_PER_CITY,
    min_users_threshold: int = DEFAULT_MIN_USERS_THRESHOLD,
    target_date: str | None = None,
    output_dir: Path | str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chạy quy trình thu thập và tổng hợp kỹ năng lập trình viên GitHub toàn quốc."""
    today_str = target_date or date.today().isoformat()
    out_dir = Path(output_dir) if output_dir else DAILY_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    auth_token = resolve_github_token(token)
    headers = get_headers(auth_token)

    if auth_token:
        print("🔑 Đã nạp GitHub Access Token (Hạn mức: 5.000 requests/giờ).")
    else:
        print("⚠️ Không có Token. Đang chạy ở chế độ ẩn danh (Hạn mức: 60 requests/giờ).")

    user_profiles = []
    skill_coverage = []
    total_cities = len(LOCATION_QUERIES)

    print(f"\n=== BẮT ĐẦU CRAWL KỸ NĂNG GITHUB ({today_str}) ===")
    print(f"Quét {total_cities} tỉnh/thành (tối đa {sample_users_per_city} users/tỉnh, ngưỡng lọc >= {min_users_threshold} hồ sơ)...")

    with httpx.Client(headers=headers, timeout=25.0) as client:
        for idx, (city_name, raw_locations) in enumerate(LOCATION_QUERIES.items(), 1):
            users = search_users_in_location(client, raw_locations, max_users=sample_users_per_city)
            total_users = len(users)

            if total_users < min_users_threshold:
                continue

            print(f"[{idx}/{total_cities}] {city_name}: Tìm thấy {total_users} hồ sơ. Đang bóc tách kỹ năng...")

            city_skills_accumulator = []
            for u in users:
                username = u.get("login")
                if not username:
                    continue

                skills = extract_user_skills(client, username)
                user_profiles.append({
                    "date": today_str,
                    "province": city_name,
                    "username": username,
                    "skills_detected": "; ".join(skills),
                    "skill_count": len(skills),
                })
                city_skills_accumulator.extend(skills)

            # Tổng hợp độ phủ kỹ năng (Top 25 kỹ năng phổ biến nhất tại tỉnh)
            counts = Counter(city_skills_accumulator)
            for skill, cnt in counts.most_common(25):
                coverage_pct = round((cnt / total_users) * 100, 2)
                skill_coverage.append({
                    "date": today_str,
                    "province": city_name,
                    "skill_name": skill,
                    "user_count_with_skill": cnt,
                    "total_users_sample": total_users,
                    "coverage_percentage": coverage_pct,
                })

    df_profiles = pd.DataFrame(user_profiles)
    df_coverage = pd.DataFrame(skill_coverage)

    profiles_file = out_dir / f"github_user_profiles_{today_str}.csv"
    coverage_file = out_dir / f"github_skill_coverage_{today_str}.csv"

    df_profiles.to_csv(profiles_file, index=False, encoding="utf-8-sig")
    df_coverage.to_csv(coverage_file, index=False, encoding="utf-8-sig")

    print(f"\n💾 Đã lưu dữ liệu hồ sơ cá nhân: {profiles_file}")
    print(f"💾 Đã lưu dữ liệu độ phủ kỹ năng: {coverage_file}")
    print("🎉 Hoàn tất quy trình crawl GitHub!")

    return df_profiles, df_coverage
