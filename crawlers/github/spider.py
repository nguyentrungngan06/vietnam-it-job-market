"""
Spider module thực hiện gọi GitHub REST API và xác thực GitHub OAuth Device Flow.
Tự động quản lý Rate Limit (primary & secondary).
"""
import os
import json
import time
from pathlib import Path
from typing import Any
import httpx
from .config import GITHUB_API_BASE, BASE_HEADERS, CLIENT_ID, TOKEN_FILE


# ==========================================
# 1. QUẢN LÝ XÁC THỰC OAUTH DEVICE FLOW
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
                print(f"Lỗi xác thực OAuth: {res.get('error_description', res.get('error'))}")
                return None
        except Exception:
            time.sleep(interval)
    return None


def get_valid_token(client_id: str | None = None, token_file: Path | str = TOKEN_FILE) -> str | None:
    """
    Lấy token hợp lệ:
    1. Ưu tiên biến môi trường GITHUB_TOKEN nếu có.
    2. Kiểm tra token đã lưu trong file cục bộ (nếu còn hợp lệ sẽ bỏ qua đăng nhập).
    3. Nếu chưa có token, kích hoạt GitHub OAuth Device Flow và lưu token vào file.
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
                        print("🔑 Token hợp lệ từ file! Bỏ qua đăng nhập.")
                        return token
        except Exception:
            pass

    c_id = client_id or CLIENT_ID or os.getenv("GITHUB_CLIENT_ID", "")
    if not c_id:
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


def get_headers(token: str | None = None) -> dict[str, str]:
    headers = dict(BASE_HEADERS)
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


# ==========================================
# 2. GỌI API & RATE LIMIT
# ==========================================
def fetch_github_api(
    client: httpx.Client,
    url: str,
    params: dict[str, Any] | None = None,
    max_retries: int = 3,
) -> dict | list | None:
    """Gửi request tới GitHub API với cơ chế tự động chờ phục hồi Rate Limit."""
    for attempt in range(max_retries):
        try:
            res = client.get(url, params=params, timeout=20.0)

            # Xử lý Rate Limit chính của GitHub
            if res.status_code == 403 and "X-RateLimit-Remaining" in res.headers:
                if int(res.headers.get("X-RateLimit-Remaining", 1)) == 0:
                    reset = int(res.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait_time = max(reset - int(time.time()) + 5, 10)
                    print(f"⚠️ Chạm giới hạn GitHub Rate Limit, tạm dừng {wait_time}s...")
                    time.sleep(wait_time)
                    continue

            # Xử lý Secondary Rate Limit
            if res.status_code in (403, 429) and "secondary rate limit" in res.text.lower():
                print("⚠️ Gặp secondary rate limit, tạm dừng 60s...")
                time.sleep(60)
                continue

            if res.status_code == 200:
                return res.json()

            if res.status_code == 404:
                return None

        except httpx.RequestError as exc:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print(f"Lỗi kết nối GitHub ({url}): {exc}")

    return None


def search_users_in_location(
    client: httpx.Client,
    raw_locations: list[str],
    max_users: int = 100,
) -> list[dict]:
    """Tìm kiếm danh sách hồ sơ GitHub theo các từ khóa địa điểm."""
    users_list = []
    seen_usernames = set()
    search_url = f"{GITHUB_API_BASE}/search/users"

    for loc in raw_locations:
        if len(users_list) >= max_users:
            break

        per_page = min(max_users - len(users_list), 100)
        data = fetch_github_api(
            client,
            search_url,
            params={
                "q": f'location:"{loc}" type:user',
                "sort": "repositories",
                "per_page": per_page,
            },
        )
        items = data.get("items", []) if isinstance(data, dict) else []
        for u in items:
            username = u.get("login")
            if username and username not in seen_usernames:
                seen_usernames.add(username)
                users_list.append(u)
            if len(users_list) >= max_users:
                break

        time.sleep(1)

    return users_list


def extract_user_skills(client: httpx.Client, username: str) -> list[str]:
    """Lấy danh sách các ngôn ngữ lập trình và chủ đề (topics) từ repositories của người dùng."""
    repos_url = f"{GITHUB_API_BASE}/users/{username}/repos"
    repos = fetch_github_api(client, repos_url, params={"type": "owner", "per_page": 30}) or []

    skills = set()
    if isinstance(repos, list):
        for r in repos:
            if not r.get("fork", False):
                lang = r.get("language")
                if lang:
                    skills.add(lang)
                topics = r.get("topics", [])
                for t in topics:
                    skills.add(t.capitalize())

    return sorted(list(skills))
