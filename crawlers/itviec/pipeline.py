"""
Module Pipeline: Khử trùng lặp (Deduplication), Gộp dữ liệu vào Master (Coalesce Update), và Lưu trữ Snapshot.
"""
import os
from datetime import date, datetime
import pandas as pd

from .config import (
    MASTER_FILE,
    SNAPSHOT_DIR,
    CRAWL_LOG_FILE,
    DEDUP_MAP_FILE,
    ORDERED_COLS,
    SALARY_COLS,
)
from .parsers import is_empty_val, infer_posted_date


def deduplicate_jobs(jobs_data):
    """
    [BƯỚC 3] Chuẩn hóa cờ has_salary và phát hiện bài đăng trùng lặp:
    - Nhóm theo (title, company, city).
    - Chọn bài đăng chính (canonical) ưu tiên theo posted_date mới nhất và có lương.
    - Đánh dấu cờ is_duplicate và canonical_job_key.
    """
    print("\n[BƯỚC 3] Chuẩn hóa dữ liệu và xử lý trùng lặp...")
    df = pd.DataFrame(jobs_data)
    if df.empty:
        return df

    # Đảm bảo cờ has_salary
    df["has_salary"] = df["salary_type"].apply(
        lambda t: str(t).strip() != "missing" if pd.notna(t) else False
    )

    df["norm_title"] = df["title"].astype(str).str.strip().str.lower()
    df["norm_comp"] = df["company"].astype(str).str.strip().str.lower()
    df["norm_city"] = df["city"].astype(str).str.strip().str.lower()

    dup_groups = df.groupby(["norm_title", "norm_comp", "norm_city"])

    dedup_mappings = []
    canonical_keys = {}
    is_duplicate_flags = {}

    group_id = 0
    for (t, c, city), g in dup_groups:
        if len(g) > 1:
            group_id += 1
            g_sorted = g.sort_values(
                by=["posted_date", "has_salary"],
                ascending=[False, False],
            )
            canonical_row = g_sorted.iloc[0]
            canon_key = canonical_row["job_key"]

            has_sal_diff = (g["salary_min"].nunique() > 1) or (g["salary_max"].nunique() > 1)
            has_desc_diff = g["description"].nunique() > 1

            for _, row_item in g.iterrows():
                is_canon = row_item["job_key"] == canon_key
                canonical_keys[row_item["job_key"]] = canon_key
                is_duplicate_flags[row_item["job_key"]] = not is_canon

                dedup_mappings.append({
                    "group_id": group_id,
                    "title": row_item["title"],
                    "company": row_item["company"],
                    "city": row_item["city"],
                    "job_key": row_item["job_key"],
                    "job_id": row_item["job_id"],
                    "posted_date": row_item["posted_date"],
                    "is_canonical": is_canon,
                    "salary_difference": has_sal_diff,
                    "description_difference": has_desc_diff,
                })
        else:
            row_item = g.iloc[0]
            canonical_keys[row_item["job_key"]] = row_item["job_key"]
            is_duplicate_flags[row_item["job_key"]] = False

    df["is_duplicate"] = df["job_key"].map(is_duplicate_flags).fillna(False).astype(bool)
    df["canonical_job_key"] = df["job_key"].map(canonical_keys)
    df.drop(columns=["norm_title", "norm_comp", "norm_city"], inplace=True)

    if dedup_mappings:
        pd.DataFrame(dedup_mappings).to_csv(DEDUP_MAP_FILE, index=False, encoding="utf-8-sig")

    # Sắp xếp các cột theo thứ tự chuẩn
    final_cols = [c for c in ORDERED_COLS if c in df.columns] + [
        c for c in df.columns if c not in ORDERED_COLS
    ]
    return df[final_cols]


def coalesce_val(old_val, new_val):
    """Giữ giá trị mới nếu khác rỗng, nếu không giữ giá trị cũ."""
    return new_val if not is_empty_val(new_val) else old_val


def update_master_and_snapshot(df_today, crawl_date=None, master_file=MASTER_FILE, snapshot_dir=SNAPSHOT_DIR, log_file=CRAWL_LOG_FILE):
    """
    [BƯỚC 4] Lưu snapshot ngày hôm nay và gộp vào file Master theo quy tắc coalesce:
    - Giá trị mới khác rỗng sẽ bổ sung/làm giàu cho dữ liệu cũ (không đè rỗng lên dữ liệu đã có).
    - Cập nhật first_seen, last_seen, days_active, is_active.
    - Ghi log thống kê số lượng và tỷ lệ lương vào crawl_log.csv.
    """
    crawl_date = crawl_date or date.today().isoformat()
    os.makedirs(snapshot_dir, exist_ok=True)

    # 1. Lưu snapshot ngày
    snap_path = os.path.join(snapshot_dir, f"itviec_clean_{crawl_date}.csv")
    df_today.to_csv(snap_path, index=False, encoding="utf-8-sig")
    print(f"\n[BƯỚC 4] Đã lưu snapshot ngày vào: '{snap_path}'")

    # 2. Gộp vào Master bằng COALESCE
    if os.path.exists(master_file):
        print(f"  -> Gộp với file Master hiện có '{master_file}'...")
        old_master = pd.read_csv(master_file, dtype=str)
        old_by_key = old_master.set_index("job_key").to_dict(orient="index")
    else:
        old_by_key = {}

    today_by_key = df_today.set_index("job_key").to_dict(orient="index")
    all_keys = list(dict.fromkeys(list(old_by_key.keys()) + list(today_by_key.keys())))

    merged_rows = []
    for k in all_keys:
        old_r = old_by_key.get(k, {})
        new_r = today_by_key.get(k, {})

        row = dict(old_r)
        if new_r:
            for col, val in new_r.items():
                if col in ("first_seen", "last_seen", "days_active", "is_active", "job_key", "job_id"):
                    continue
                row[col] = coalesce_val(row.get(col), val)

            first_s = old_r.get("first_seen")
            last_s = old_r.get("last_seen")
            row["first_seen"] = min(str(first_s), crawl_date) if not is_empty_val(first_s) else crawl_date
            row["last_seen"] = max(str(last_s), crawl_date) if not is_empty_val(last_s) else crawl_date
        else:
            row["first_seen"] = old_r.get("first_seen", crawl_date)
            row["last_seen"] = old_r.get("last_seen", crawl_date)

        row["job_key"] = k
        if is_empty_val(row.get("posted_date")):
            row["posted_date"] = infer_posted_date(row["first_seen"])
        merged_rows.append(row)

    df_master = pd.DataFrame(merged_rows)
    max_seen = df_master["last_seen"].max()
    df_master["is_active"] = df_master["last_seen"] == max_seen
    df_master["days_active"] = (
        pd.to_datetime(df_master["last_seen"]) - pd.to_datetime(df_master["first_seen"])
    ).dt.days + 1

    # Đảm bảo thứ tự cột
    final_master_cols = [c for c in ORDERED_COLS if c in df_master.columns] + [
        c for c in df_master.columns if c not in ORDERED_COLS
    ]
    df_master = df_master[final_master_cols]
    df_master.to_csv(master_file, index=False, encoding="utf-8-sig")
    print(f"  -> Đã cập nhật file Master: {len(df_master)} việc làm.")

    # 3. Ghi Crawl Log
    total_today = len(df_today)
    sal_vis_cnt = int((df_today["salary_visible"] == True).sum())
    has_sal_cnt = int(df_today["has_salary"].sum())
    sal_ratio = sal_vis_cnt / max(total_today, 1)
    status = "partial" if sal_vis_cnt == 0 or sal_ratio < 0.10 else "ok"
    note = "0 tin có lương trực tiếp (kiểm tra auth.json)" if status == "partial" else "Đầy đủ nhãn lương"

    log_entry = pd.DataFrame([{
        "crawl_date": crawl_date,
        "source_file": os.path.basename(snap_path),
        "total_jobs": total_today,
        "unique_jobs": total_today,
        "salary_visible_jobs": sal_vis_cnt,
        "salary_parsed_jobs": has_sal_cnt,
        "salary_visible_ratio": round(sal_ratio, 4),
        "status": status,
        "note": note,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }])

    if os.path.exists(log_file):
        old_log = pd.read_csv(log_file, dtype=str)
        old_log = old_log[old_log["crawl_date"] != crawl_date]
        combined_log = pd.concat([old_log, log_entry], ignore_index=True)
    else:
        combined_log = log_entry
    combined_log.to_csv(log_file, index=False, encoding="utf-8-sig")

    return df_master
