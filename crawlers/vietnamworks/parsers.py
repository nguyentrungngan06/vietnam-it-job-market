"""
Trích xuất và chuẩn hóa dữ liệu tin tuyển dụng VietnamWorks.
"""
import json
import re
from typing import Any
import pandas as pd

from .config import USD_VND_RATE

# Regex bóc tách số lượt xem và ứng tuyển
_RE_VIEWS = re.compile(r'numOfViews\\*"\s*:\s*(\d+)')
_RE_APPS = re.compile(r'numOfApplications\\*"\s*:\s*(\d+)')

# Regex bóc tách Next.js flight payload cho mô tả/yêu cầu đầy đủ
_RE_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
_RE_HDR = re.compile(rb"([0-9a-fA-F]+):")
_RE_TXT = re.compile(rb"T([0-9a-fA-F]+),")
_RE_REF = {
    "description": re.compile(rb'jobDescription\\*":\\*"\$([0-9a-fA-F]+)'),
    "requirement": re.compile(rb'jobRequirement\\*":\\*"\$([0-9a-fA-F]+)'),
}
_KEYS = {
    "description": "jobDescription",
    "requirement": "jobRequirement",
}


def clean_html(text: str | None) -> str:
    """Xóa bỏ các thẻ HTML giống hệt parse.py để giữ nguyên định dạng dữ liệu."""
    return re.sub(r"<[^>]+>", " ", text or "")


def _first_or_none(lst: Any) -> Any:
    return lst[0] if isinstance(lst, list) and lst else None


def parse_job_item(j: dict) -> dict:
    """Chuyển đổi 1 item JSON từ Search API thành dict chuẩn."""
    pretty = j.get("prettySalary") or ""
    visible = bool(j.get("isSalaryVisible")) and (j.get("salaryMax") or 0) > 0
    loc = _first_or_none(j.get("workingLocations")) or {}
    ind = _first_or_none(j.get("industriesV3")) or {}
    jf = j.get("jobFunctionsV3") or {}

    skills = j.get("skills") or []
    skills_str = "|".join(s["skillName"] for s in skills if isinstance(s, dict) and "skillName" in s)

    return {
        "job_id": j.get("jobId"),
        "title": j.get("jobTitle"),
        "company": j.get("companyName"),
        "company_id": j.get("companyId"),
        "url": j.get("jobUrl"),
        "level": j.get("jobLevelVI"),
        "industry": ind.get("industryV3NameVI"),
        "job_function": jf.get("jobFunctionV3Name"),
        "city": loc.get("cityNameVI"),
        "salary_visible": visible,
        "salary_min": j.get("salaryMin") if visible else None,
        "salary_max": j.get("salaryMax") if visible else None,
        "currency": j.get("salaryCurrency") if visible else None,
        "salary_period": ("year" if "/năm" in pretty else "month") if visible else None,
        "salary_text": pretty,
        "skills": skills_str,
        "posted_on": j.get("approvedOn"),
        "expired_on": j.get("expiredOn"),
        "description": clean_html(j.get("jobDescription")),
        "requirement": clean_html(j.get("jobRequirement")),
    }


def add_salary_vnd(df: pd.DataFrame) -> pd.DataFrame:
    """Tính toán và quy đổi mức lương về đơn vị triệu VND / tháng."""
    if df.empty:
        df["salary_min_mvnd_month"] = None
        df["salary_max_mvnd_month"] = None
        df["salary_mid_mvnd_month"] = None
        return df

    rate = df["currency"].map({"VND": 1, "USD": USD_VND_RATE}).fillna(1)
    div = df["salary_period"].map({"month": 1, "year": 12}).fillna(1)

    for c in ("min", "max"):
        col = f"salary_{c}"
        if col in df.columns:
            df[f"salary_{c}_mvnd_month"] = (df[col] * rate / div / 1e6).round(2)
        else:
            df[f"salary_{c}_mvnd_month"] = None

    df["salary_mid_mvnd_month"] = (
        (df["salary_min_mvnd_month"] + df["salary_max_mvnd_month"]) / 2
    ).round(2)
    return df


def parse_detail_page(html: str) -> dict[str, str]:
    """
    Trích xuất views, applications, và full description/requirement từ HTML trang chi tiết Next.js.
    """
    v, a = _RE_VIEWS.search(html), _RE_APPS.search(html)
    res = {
        "views": v.group(1) if v else "",
        "applications": a.group(1) if a else "",
        "description": "",
        "requirement": "",
    }

    # Bóc tách flight chunks của Next.js
    chunks = []
    for p in _RE_PUSH.findall(html):
        try:
            chunks.append(json.loads('"' + p + '"'))
        except ValueError:
            pass
    flight = "".join(chunks).encode("utf-8")

    rows, pos = {}, 0
    while pos < len(flight):
        m = _RE_HDR.match(flight, pos)
        if m:
            tm = _RE_TXT.match(flight[m.end():m.end() + 12])
            if tm:
                n, start = int(tm.group(1), 16), m.end() + tm.end()
                rows[m.group(1).decode()] = flight[start:start + n].decode("utf-8", "ignore")
                pos = start + n
                continue
        nl = flight.find(b"\n", pos)
        if nl < 0:
            break
        pos = nl + 1

    for key, rx in _RE_REF.items():
        # 1. Thử lấy từ tham chiếu chunk $id
        for m in rx.finditer(flight):
            txt = rows.get(m.group(1).decode())
            if txt:
                res[key] = clean_html(txt)
                break

        # 2. Dự phòng: nếu text được nhúng thẳng trong JSON
        if not res[key]:
            field_name = _KEYS[key].encode()
            rx_inline = re.compile(rb'"' + field_name + rb'"\s*:\s*"((?:[^"\\]|\\.)*)"')
            for m in rx_inline.finditer(flight):
                raw_bytes = m.group(1)
                if raw_bytes.startswith(b"$"):
                    continue
                try:
                    val = json.loads(b'"' + raw_bytes + b'"')
                    if val and len(val.strip()) > len(res[key]):
                        res[key] = clean_html(val)
                except Exception:
                    pass

    return res
