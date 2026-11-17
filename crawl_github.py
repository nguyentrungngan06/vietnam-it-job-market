"""
GitHub Vietnam Developer Skills Crawler
Cào và phân tích kỹ năng lập trình viên theo tỉnh/thành tại Việt Nam từ GitHub.
Hỗ trợ xác thực OAuth Device Flow, tự động lưu token và tối ưu cho crawl hàng ngày.
"""
import os
import json
import time
import argparse
from datetime import datetime
from collections import Counter
from pathlib import Path
import httpx
import pandas as pd

# Điền Client ID OAuth App của bạn vào đây hoặc truyền qua biến môi trường GITHUB_CLIENT_ID
CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
TOKEN_FILE = ".github_token.json"

# ==========================================
# 1. QUẢN LÝ XÁC THỰC (OAUTH DEVICE FLOW)
# ==========================================
def get_device_code(client_id: str) -> dict:
    url = "https://github.com/login/device/code"
    payload = {"client_id": client_id, "scope": "read:user repo"}
    res = httpx.post(url, data=payload, headers={"Accept": "application/json"}, timeout=10.0)
    return res.json()


def poll_for_token(client_id: str, device_code: str, interval: int = 5, expires_in: int = 900) -> str | None:
    url = "https://github.com/login/oauth/access_token"
    payload = {
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    start_time = time.time()
    while time.time() - start_time < expires_in:
        time.sleep(interval)
        try:
            res = httpx.post(url, data=payload, headers={"Accept": "application/json"}, timeout=10.0).json()
            if "access_token" in res:
                return res["access_token"]
            elif res.get("error") == "slow_down":
                interval += 5
            elif res.get("error") not in ("authorization_pending", None):
                print(f"Lỗi xác thực: {res.get('error_description', res.get('error'))}")
                return None
        except Exception:
            time.sleep(interval)
    return None


def get_valid_token(client_id: str | None = None, token_file: str = TOKEN_FILE) -> str | None:
    """
    Lấy token hợp lệ:
    1. Ưu tiên biến môi trường GITHUB_TOKEN nếu có.
    2. Kiểm tra token đã lưu trong file cục bộ (bỏ qua đăng nhập nếu còn hợp lệ).
    3. Nếu chưa có, kích hoạt GitHub OAuth Device Flow và lưu lại token.
    """
    env_token = os.getenv("GITHUB_TOKEN")
    if env_token:
        return env_token.strip()

    p_file = Path(token_file)
    if p_file.exists():
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                token = json.load(f).get("access_token")
                if token:
                    check = httpx.get("https://api.github.com/user", headers={"Authorization": f"token {token}"}, timeout=6.0)
                    if check.status_code == 200:
                        print("🔑 Token hợp lệ! Bỏ qua đăng nhập.")
                        return token
        except Exception:
            pass

    c_id = client_id or CLIENT_ID or os.getenv("GITHUB_CLIENT_ID", "")
    if not c_id:
        print("⚠️ Chưa có Client ID OAuth App. Vui lòng điền CLIENT_ID, thiết lập GITHUB_CLIENT_ID hoặc truyền --client-id.")
        return None

    print("\n🔐 BẮT ĐẦU ĐĂNG NHẬP GITHUB DEVICE FLOW")
    d_data = get_device_code(c_id)
    if "user_code" not in d_data:
        print(f"❌ Không lấy được mã xác thực: {d_data}")
        return None

    print(f"1. Truy cập: {d_data.get('verification_uri', 'https://github.com/login/device')}")
    print(f"2. Nhập mã: 👉  {d_data.get('user_code')}  👈")

    token = poll_for_token(
        client_id=c_id,
        device_code=d_data["device_code"],
        interval=d_data.get("interval", 5),
        expires_in=d_data.get("expires_in", 900),
    )
    if token:
        try:
            with open(p_file, "w", encoding="utf-8") as f:
                json.dump({"access_token": token}, f)
            print("💾 Đã lưu token thành công vào file!")
        except Exception:
            pass
        return token

    return None


# ==========================================
# 2. CẤU HÌNH ĐỊA ĐIỂM CÁC TỈNH/THÀNH PHỐ
# ==========================================
LOCATION_QUERIES = {
    # Đô thị lớn & Trung tâm công nghệ
    "Hà Nội": ["Hanoi", "Ha Noi", "Hà Nội", "HN"],
    "TP. Hồ Chí Minh": ["Ho Chi Minh", "HoChiMinh", "HCM", "Saigon", "Sai Gon", "TPHCM"],
    "Đà Nẵng": ["Da Nang", "Danang", "Đà Nẵng"],
    "Hải Phòng": ["Hai Phong", "Hải Phòng"],
    "Cần Thơ": ["Can Tho", "Cần Thơ"],
    # Miền Bắc
    "Bắc Ninh": ["Bac Ninh", "Bắc Ninh"],
    "Bắc Giang": ["Bac Giang", "Bắc Giang"],
    "Quảng Ninh": ["Quang Ninh", "Quảng Ninh"],
    "Hải Dương": ["Hai Duong", "Hải Dương"],
    "Hưng Yên": ["Hung Yen", "Hưng Yên"],
    "Vĩnh Phúc": ["Vinh Phuc", "Vĩnh Phúc"],
    "Thái Nguyên": ["Thai Nguyen", "Thái Nguyên"],
    "Phú Thọ": ["Phu Tho", "Phú Thọ"],
    "Nam Định": ["Nam Dinh", "Nam Định"],
    "Ninh Bình": ["Ninh Binh", "Ninh Bình"],
    "Thái Bình": ["Thai Binh", "Thái Bình"],
    "Hà Nam": ["Ha Nam", "Hà Nam"],
    "Hòa Bình": ["Hoa Binh", "Hòa Bình"],
    "Lạng Sơn": ["Lang Son", "Lạng Sơn"],
    "Lào Cai": ["Lao Cai", "Lào Cai"],
    "Yên Bái": ["Yen Bai", "Yên Bái"],
    "Sơn La": ["Son La", "Sơn La"],
    "Tuyên Quang": ["Tuyen Quang", "Tuyên Quang"],
    "Bắc Kạn": ["Bac Kan", "Bắc Kạn"],
    "Cao Bằng": ["Cao Bang", "Cao Bằng"],
    "Điện Biên": ["Dien Bien", "Điện Biên"],
    "Lai Châu": ["Lai Chau", "Lai Châu"],
    "Hà Giang": ["Ha Giang", "Hà Giang"],
    # Miền Trung & Tây Nguyên
    "Thừa Thiên Huế": ["Hue", "Thua Thien Hue", "Huế"],
    "Quảng Nam": ["Quang Nam", "Quảng Nam", "Hoi An"],
    "Quảng Ngãi": ["Quang Ngai", "Quảng Ngãi"],
    "Bình Định": ["Binh Dinh", "Quy Nhon", "Bình Định"],
    "Phú Yên": ["Phu Yen", "Tuy Hoa", "Phú Yên"],
    "Khánh Hòa": ["Nha Trang", "Khanh Hoa", "Khánh Hòa"],
    "Ninh Thuận": ["Ninh Thuan", "Phan Rang", "Ninh Thuận"],
    "Bình Thuận": ["Binh Thuan", "Phan Thiet", "Bình Thuận"],
    "Thanh Hóa": ["Thanh Hoa", "Thanh Hóa"],
    "Nghệ An": ["Nghe An", "Vinh", "Nghệ An"],
    "Hà Tĩnh": ["Ha Tinh", "Hà Tĩnh"],
    "Quảng Bình": ["Quang Binh", "Quảng Bình"],
    "Quảng Trị": ["Quang Tri", "Quảng Trị"],
    "Lâm Đồng": ["Da Lat", "Dalat", "Lam Dong", "Lâm Đồng"],
    "Đắk Lắk": ["Dak Lak", "Buon Ma Thuot", "Đắk Lắk"],
    "Gia Lai": ["Gia Lai", "Pleiku"],
    "Đắk Nông": ["Dak Nong", "Đắk Nông"],
    "Kon Tum": ["Kon Tum"],
    # Miền Nam
    "Bình Dương": ["Binh Duong", "Bình Dương"],
    "Đồng Nai": ["Dong Nai", "Bien Hoa", "Đồng Nai"],
    "Bà Rịa - Vũng Tàu": ["Vung Tau", "Ba Ria", "Vũng Tàu"],
    "Long An": ["Long An", "Tan An"],
    "Tiền Giang": ["Tien Giang", "My Tho", "Tiền Giang"],
    "Bến Tre": ["Ben Tre", "Bến Tre"],
    "Trà Vinh": ["Tra Vinh", "Trà Vinh"],
    "Vĩnh Long": ["Vinh Long", "Vĩnh Long"],
    "Đồng Tháp": ["Dong Thap", "Cao Lanh", "Đồng Tháp"],
    "An Giang": ["An Giang", "Long Xuyen", "An Giang"],
    "Kiên Giang": ["Kien Giang", "Rach Gia", "Phu Quoc"],
    "Hậu Giang": ["Hau Giang", "Hậu Giang"],
    "Sóc Trăng": ["Soc Trang", "Sóc Trăng"],
    "Bạc Liêu": ["Bac Lieu", "Bạc Liêu"],
    "Cà Mau": ["Ca Mau", "Cà Mau"],
    "Bình Phước": ["Binh Phuoc", "Bình Phước"],
    "Tây Ninh": ["Tay Ninh", "Tây Ninh"],
}


# ==========================================
# 3. GỌI API & XỬ LÝ RATE LIMIT
# ==========================================
def fetch_github(url: str, headers: dict, params: dict | None = None, retries: int = 3):
    """Gửi yêu cầu tới GitHub API và tự động xử lý Rate Limit."""
    for attempt in range(retries):
        try:
            res = httpx.get(url, headers=headers, params=params, timeout=20.0)

            # Xử lý Rate Limit chính
            if res.status_code == 403 and "X-RateLimit-Remaining" in res.headers:
                if int(res.headers.get("X-RateLimit-Remaining", 1)) == 0:
                    reset = int(res.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait_time = max(reset - int(time.time()) + 5, 10)
                    print(f"⚠️ Chạm Rate Limit GitHub, tạm dừng {wait_time}s...")
                    time.sleep(wait_time)
                    continue

            # Xử lý secondary rate limit
            if res.status_code in (403, 429) and "secondary rate limit" in res.text.lower():
                print("⚠️ Gặp secondary rate limit, tạm dừng 60s...")
                time.sleep(60)
                continue

            if res.status_code == 200:
                return res.json()

            if res.status_code == 404:
                return None

        except httpx.RequestError as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print(f"Lỗi kết nối ({url}): {e}")

    return None


# ==========================================
# 4. PIPELINE CÀO & PHÂN TÍCH KỸ NĂNG
# ==========================================
def crawl_user_profile_skills(
    headers: dict,
    sample_users_per_city: int = 100,
    min_users_threshold: int = 5,
    output_dir: str = ".",
):
    user_skill_profiles = []
    city_summary = []
    total_cities = len(LOCATION_QUERIES)

    print(f"🚀 Bắt đầu quét {total_cities} tỉnh/thành (tối đa {sample_users_per_city} users/tỉnh)...")

    for idx_city, (city_clean, raw_locations) in enumerate(LOCATION_QUERIES.items(), 1):
        users_list = []
        seen_usernames = set()

        for loc in raw_locations:
            if len(users_list) >= sample_users_per_city:
                break

            user_search_url = "https://api.github.com/search/users"
            per_page = min(sample_users_per_city - len(users_list), 100)
            user_res = fetch_github(
                user_search_url,
                headers,
                {"q": f'location:"{loc}" type:user', "per_page": per_page, "sort": "repositories"},
            )

            items = user_res.get("items", []) if user_res else []
            for u in items:
                username = u.get("login")
                if username and username not in seen_usernames:
                    seen_usernames.add(username)
                    users_list.append(u)
                if len(users_list) >= sample_users_per_city:
                    break

            time.sleep(1)

        total_scanned = len(users_list)
        if total_scanned < min_users_threshold:
            continue

        print(f"[{idx_city}/{total_cities}] {city_clean}: Đang phân tích {total_scanned} hồ sơ...")

        all_city_skills = []
        for u in users_list:
            username = u.get("login")
            repos_url = f"https://api.github.com/users/{username}/repos"
            user_repos = fetch_github(repos_url, headers, {"type": "owner", "per_page": 30}) or []

            user_skills = set()
            for r in user_repos:
                if not r.get("fork", False):
                    lang = r.get("language")
                    if lang:
                        user_skills.add(lang)
                    topics = r.get("topics", [])
                    for t in topics:
                        user_skills.add(t.capitalize())

            skills_list = sorted(list(user_skills))
            user_skill_profiles.append({
                "province_clean": city_clean,
                "username": username,
                "skills_detected": "; ".join(skills_list),
                "skill_count": len(skills_list),
            })
            all_city_skills.extend(skills_list)
            time.sleep(0.5)

        # Tính tỷ lệ % độ phủ kỹ năng
        skill_counts = Counter(all_city_skills)
        for skill_name, count in skill_counts.most_common(20):
            percentage = round((count / total_scanned) * 100, 2)
            city_summary.append({
                "province_clean": city_clean,
                "skill_name": skill_name,
                "user_count_with_skill": count,
                "total_sample_users": total_scanned,
                "coverage_percentage": percentage,
            })

    # Lưu kết quả
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")

    df_profiles = pd.DataFrame(user_skill_profiles)
    df_coverage = pd.DataFrame(city_summary)

    profiles_file = out_path / f"github_user_profiles_{today_str}.csv"
    coverage_file = out_path / f"github_skill_coverage_{today_str}.csv"

    df_profiles.to_csv(profiles_file, index=False, encoding="utf-8-sig")
    df_coverage.to_csv(coverage_file, index=False, encoding="utf-8-sig")

    print(f"\n💾 Đã lưu hồ sơ chi tiết: {profiles_file}")
    print(f"💾 Đã lưu độ phủ kỹ năng: {coverage_file}")
    print("🎉 Hoàn tất quy trình crawl GitHub!")
    return df_profiles, df_coverage


def main():
    parser = argparse.ArgumentParser(description="GitHub Vietnam Developer Skills Crawler")
    parser.add_argument("--client-id", type=str, default=None, help="GitHub OAuth App Client ID")
    parser.add_argument("--users-per-city", type=int, default=100, help="Số users tối đa mỗi tỉnh (mặc định: 100)")
    parser.add_argument("--min-users", type=int, default=5, help="Ngưỡng tối thiểu hồ sơ để xử lý tỉnh (mặc định: 5)")
    parser.add_argument("--output-dir", type=str, default=".", help="Thư mục lưu file CSV đầu ra (mặc định: thư mục hiện tại)")

    args = parser.parse_args()
    token = get_valid_token(client_id=args.client_id)

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    crawl_user_profile_skills(
        headers=headers,
        sample_users_per_city=args.users_per_city,
        min_users_threshold=args.min_users,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
