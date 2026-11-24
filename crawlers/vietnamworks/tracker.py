"""
Theo dõi vòng đời tin tuyển dụng (Job Lifecycle Tracking) và lưu trữ Master / Daily.
"""
import csv
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

from .config import DAILY_DIR, MASTER_DIR, MASTER_FILE

TRACKING_EXTRA = [
    "first_seen", "last_seen", "days_alive", "times_seen", "status", "gone_on",
    "posted_first", "observed_days_alive", "planned_days", "days_to_expire",
    "end_reason", "views_first", "views_per_day"
]
DAILY_EXTRA = ["is_new"] + TRACKING_EXTRA


def _to_date(val: Any) -> date | None:
    """Chuyển đổi chuỗi ngày tháng ISO sang đối tượng date."""
    if not val or pd.isna(val):
        return None
    try:
        return date.fromisoformat(str(val)[:10])
    except (ValueError, TypeError):
        return None


def _to_float(val: Any) -> float | None:
    if val is None or pd.isna(val):
        return None
    try:
        s = str(val).replace(",", "").strip()
        return float(s) if s else None
    except ValueError:
        return None


def _day_span(a: date | None, b: date | None) -> str:
    """Số ngày giữa a và b (tính cả 2 đầu: a=b -> 1)."""
    return str((b - a).days + 1) if (a and b) else ""


def _refresh_lifecycle(row: dict, today: date) -> None:
    """Tính toán lại các chỉ số vòng đời từ ngày đăng, ngày hết hạn và ngày cuối thấy."""
    posted = _to_date(row.get("posted_first"))
    expire = _to_date(row.get("expired_on"))
    last = _to_date(row.get("last_seen"))

    row["observed_days_alive"] = _day_span(posted, last)
    row["planned_days"] = _day_span(posted, expire)

    if row.get("status") == "active" and expire:
        row["days_to_expire"] = str((expire - today).days)
    else:
        row["days_to_expire"] = ""

    if row.get("status") == "gone":
        gone_on = _to_date(row.get("gone_on"))
        if expire and gone_on and gone_on > expire:
            row["end_reason"] = "expired"
        else:
            row["end_reason"] = "removed_early"
    else:
        row["end_reason"] = ""

    views_num = _to_float(row.get("views"))
    age_num = _to_float(row.get("observed_days_alive"))
    if views_num is not None and age_num and age_num > 0:
        row["views_per_day"] = f"{views_num / age_num:.1f}"
    else:
        row["views_per_day"] = ""


def update_master_and_daily(
    current_jobs: list[dict],
    base_fields: list[str],
    today: str | None = None,
    is_complete_crawl: bool = True,
) -> tuple[int, int, int]:
    """
    Cập nhật dữ liệu vào Master và ghi snapshot Daily.
    Trả về: (tổng số tin thấy, số tin mới hôm nay, số tin đã biến mất).
    """
    today_str = today or date.today().isoformat()
    today_date = date.fromisoformat(today_str)

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_DIR.mkdir(parents=True, exist_ok=True)

    # Đảm bảo có cột views trong base_fields để cấu trúc ổn định
    fields_order = list(base_fields)
    if "views" not in fields_order:
        fields_order.append("views")

    # Đọc Master hiện tại nếu có
    master: dict[str, dict] = {}
    if MASTER_FILE.exists():
        with MASTER_FILE.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and "job_id" in reader.fieldnames:
                master = {r["job_id"]: r for r in reader if r.get("job_id")}

    # Đọc cache fulltext nếu có để tự động làm giàu tin bị cắt ngắn
    fulltext_cache: dict[str, dict] = {}
    fulltext_file = Path("data/fulltext/fulltext.csv")
    if fulltext_file.exists():
        with fulltext_file.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("description") and not (r["description"].strip().endswith("...") or r["description"].strip().endswith("…")):
                    fulltext_cache[str(r["job_id"])] = r

    current_map = {str(r["job_id"]): r for r in current_jobs if r.get("job_id")}

    daily_rows = []
    new_count = 0

    for jid, cur_row in current_map.items():
        row = master.get(jid)
        if row is None:
            row = {"first_seen": today_str, "times_seen": "0"}
            master[jid] = row
            new_count += 1

        # Bảo toàn mô tả đầy đủ: không để bản cắt ngắn "..." từ Search API ghi đè bản full
        for col in ("description", "requirement"):
            orig_val = (row.get(col) or "").strip()
            new_val = (cur_row.get(col) or "").strip()
            if orig_val and not (orig_val.endswith("...") or orig_val.endswith("…")):
                if new_val.endswith("...") or new_val.endswith("…") or len(new_val) < len(orig_val):
                    cur_row[col] = orig_val
            elif not orig_val or orig_val.endswith("...") or orig_val.endswith("…"):
                cached_r = fulltext_cache.get(jid)
                if cached_r:
                    c_val = (cached_r.get(col) or "").strip()
                    if c_val and not (c_val.endswith("...") or c_val.endswith("…")):
                        cur_row[col] = c_val

        # Cập nhật thông tin chi tiết mới nhất
        row.update(cur_row)

        if not row.get("posted_first"):
            p = _to_date(row.get("posted_on"))
            row["posted_first"] = p.isoformat() if p else ""

        # Tránh tăng times_seen nếu chạy lại nhiều lần trong cùng 1 ngày
        if row.get("last_seen") != today_str:
            row["times_seen"] = str(int(row.get("times_seen", 0)) + 1)

        if not row.get("views_first") and str(row.get("views", "")).strip() != "":
            row["views_first"] = row["views"]

        row["last_seen"] = today_str
        row["days_alive"] = _day_span(_to_date(row["first_seen"]), today_date)
        row["status"] = "active"
        row["gone_on"] = ""

        _refresh_lifecycle(row, today_date)
        daily_rows.append({**row, "is_new": int(row["first_seen"] == today_str)})

    # Đánh dấu các tin không còn xuất hiện là "gone" (nếu crawl đầy đủ mọi trang)
    gone_count = 0
    if is_complete_crawl:
        for row in master.values():
            if row.get("last_seen") != today_str and row.get("status") == "active":
                row["status"] = "gone"
                row["gone_on"] = today_str
                gone_count += 1

    # Làm mới lại các tin đã gone
    for row in master.values():
        if row.get("status") == "gone":
            p = _to_date(row.get("posted_on"))
            if not row.get("posted_first") and p:
                row["posted_first"] = p.isoformat()
            if not row.get("gone_on") and _to_date(row.get("last_seen")):
                row["gone_on"] = (_to_date(row["last_seen"]) + timedelta(days=1)).isoformat()
            _refresh_lifecycle(row, today_date)

    # Ghi file Daily Snapshot
    daily_file = DAILY_DIR / f"vietnamworks_{today_str}.csv"
    with daily_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order + DAILY_EXTRA, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(daily_rows)

    # Ghi file Master
    with MASTER_FILE.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order + TRACKING_EXTRA, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(list(master.values()))

    return len(current_map), new_count, gone_count
