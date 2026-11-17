"""
Spider module thực hiện gọi GitHub REST API để tìm kiếm users và lấy thông tin kỹ năng qua repositories.
Tự động quản lý Rate Limit (primary & secondary).
"""
import time
import httpx
from typing import Any
from .config import GITHUB_API_BASE, BASE_HEADERS


def get_headers(token: str | None = None) -> dict[str, str]:
    headers = dict(BASE_HEADERS)
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


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

            # Xử lý Secondary Rate Limit / Lạm dụng tần suất
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
