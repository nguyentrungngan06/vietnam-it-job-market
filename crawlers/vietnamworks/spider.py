"""
HTTP Client và thu thập dữ liệu (Search API & Chi tiết tin) VietnamWorks.
"""
import random
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from typing import Generator

import httpx

from .config import (
    SEARCH_API,
    SEARCH_HEADERS,
    DETAIL_HEADERS,
    IT_FILTER,
    RETRIEVE_FIELDS,
    HITS_PER_PAGE,
    USER_AGENT,
)


class BlockedError(Exception):
    """Lỗi khi bị chặn hoặc gặp captcha/challenge."""
    pass


_robots_cache: dict[str, RobotFileParser | None] = {}


def polite_sleep(low: float = 1.5, high: float = 3.0) -> None:
    """Tạm dừng ngẫu nhiên giữa các request để tuân thủ phép lịch sự thu thập."""
    time.sleep(random.uniform(low, high))


def is_allowed_by_robots(url: str) -> bool:
    """Kiểm tra robots.txt của domain trước khi cào."""
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots_cache:
        try:
            r = httpx.get(
                f"{base}/robots.txt",
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                follow_redirects=True,
            )
            if r.status_code == 200 and "<html" not in r.text[:300].lower():
                rp = RobotFileParser()
                rp.parse(r.text.splitlines())
                _robots_cache[base] = rp
            elif 400 <= r.status_code < 500 and r.status_code not in (401, 403):
                _robots_cache[base] = None
            else:
                return False
        except Exception:
            return False

    rp = _robots_cache[base]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def check_response(resp: httpx.Response) -> None:
    """Kiểm tra phản hồi xem có bị chặn hoặc xuất hiện challenge/captcha không."""
    if resp.status_code in (403, 429) or "captcha" in resp.text[:3000].lower():
        raise BlockedError(f"{resp.status_code}/captcha tại {resp.url}")


def build_search_payload(page: int, hits_per_page: int = HITS_PER_PAGE) -> dict:
    """Tạo payload gọi Search API."""
    return {
        "userId": 0,
        "query": "",
        "filter": IT_FILTER,
        "ranges": [],
        "order": [],
        "hitsPerPage": hits_per_page,
        "page": page,
        "retrieveFields": RETRIEVE_FIELDS,
        "summaryVersion": "",
    }


def crawl_search_pages(
    client: httpx.Client,
    max_pages: int = 30,
) -> Generator[tuple[int, int, list[dict]], None, None]:
    """
    Quét qua các trang của Search API.
    Yields (current_page, total_pages, items_list).
    """
    if not is_allowed_by_robots(SEARCH_API):
        raise BlockedError("robots.txt của ms.vietnamworks.com không cho phép crawl.")

    page, total_pages = 0, None
    while page < max_pages and (total_pages is None or page < total_pages):
        polite_sleep()
        resp = client.post(SEARCH_API, json=build_search_payload(page))
        check_response(resp)
        resp.raise_for_status()

        data = resp.json()
        meta = data.get("meta", {})
        total_pages = meta.get("nbPages", 1)
        items = data.get("data", [])

        yield page + 1, total_pages, items
        page += 1


def fetch_detail_html(client: httpx.Client, url: str) -> str | None:
    """Tải HTML trang chi tiết tin tuyển dụng."""
    if not is_allowed_by_robots(url):
        return None
    try:
        polite_sleep(1.0, 2.0)
        resp = client.get(url, headers=DETAIL_HEADERS, follow_redirects=True)
        check_response(resp)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None
