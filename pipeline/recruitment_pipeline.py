#!/usr/bin/env python3
"""Unified Recruitment Data Pipeline.

Handles:
1. Snapshot Aggregation & Master Dataset Creation (<= cutoff date)
2. VietnamWorks JD Enrichment from vietnamworks_jobs.csv (resolving truncated JDs)
3. Cross-Platform Join (ITViec + VietnamWorks)
4. Text Cleaning (HTML entities, boilerplate stripping, whitespace collapse)
5. City Normalization (Hà Nội, Hồ Chí Minh, Đà Nẵng, etc.)
6. Salary Parsing:
   - dot-thousands separator, VND priority, "Từ X" floor handling
   - Gross / Net classification
   - title salary fallback, non-salary rejection, manual fixes from manual_overrides/
7. Skill Taxonomy & Alias Mapping:
   - 2-tier structure (skill, skill_family, skill_category)
   - Compound skill splitting ("Java/.Net/Python" -> separate skills)
   - Low-confidence / needs_human_check flagging
8. Deduplication & Time Harmonization:
   - company + title + city matching
   - Unified first_seen (min), last_seen (max), and is_active (any)
   - n_postings_in_group tracking and 20-sample audit table
9. Left-censoring detection (first_seen <= 2026-10-11)
10. Column & Company Standardization (resolving headhunter clients, dropping dead columns)

Usage:
  python recruitment_pipeline.py --from-snapshots --cutoff 2026-10-25 --out hr_pipeline_output
"""
from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import html
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from jd_analysis import classify_skill, extract_experience, extract_level, infer_level_from_experience

try:
    from rapidfuzz.fuzz import ratio as fuzzy_ratio
except ImportError:
    from difflib import SequenceMatcher

    def fuzzy_ratio(a, b):
        return 100 * SequenceMatcher(None, str(a), str(b)).ratio()


USD_TO_VND = 25000
MONTHLY_WORKING_DAYS = 22

COMPANY_STOP = re.compile(
    r"\b(?:ngan hang thuong mai co phan|thuong mai co phan|tmcp|cong ty|co phan|tnhh|mtv|"
    r"trach nhiem huu han|joint stock|company|limited|ltd|jsc|corp|corporation|inc|plc|pte|gmbh|"
    r"co|vietnam|viet nam|chi nhanh|van phong dai dien)\b"
)

SKILL_ALIASES = {
    'agile': 'Agile & Scrum', 'scrum': 'Agile & Scrum',
    'cloud': 'Cloud Computing', 'api': 'API Development',
    'react': 'React', 'reactjs': 'React', 'react.js': 'React',
    'angular': 'Angular', 'angularjs': 'Angular',
    'vue': 'Vue.js', 'vuejs': 'Vue.js', 'vue.js': 'Vue.js',
    'docker': 'Docker', 'kubernetes': 'Kubernetes', 'k8s': 'Kubernetes',
    'c++': 'C/C++', 'c language': 'C/C++',
    'oracle': 'Oracle Database', 'automation test': 'Test Automation',
    'qa qc': 'Quality Management (QA/QC)', 'tester': 'Software Testing',
    'microservices': 'Software Architecture & Design',
    'software architecture': 'Software Architecture & Design',
    'azure': 'Microsoft Azure', 'leadership': 'Leadership & People Management',
    'team management': 'Leadership & People Management',
    'system admin': 'IT Infrastructure & System Administration',
    'security': 'Cybersecurity', 'product owner': 'Product Management',
    'database': 'Database Design',
    'js': 'JavaScript', 'javascript': 'JavaScript',
    'typescript': 'TypeScript', 'nodejs': 'Node.js', 'node js': 'Node.js',
    'power bi': 'Power BI', 'powerbi': 'Power BI',
    'business analyst': 'Business Analysis (BA)', 'business analysis': 'Business Analysis (BA)',
    'it business analysis': 'Business Analysis (BA)', 'phan tich nghiep vu': 'Business Analysis (BA)',
    'bussiness analyst': 'Business Analysis (BA)', 'ba': 'Business Analysis (BA)',
    'ai': 'Artificial Intelligence (AI)', 'artificial intelligence': 'Artificial Intelligence (AI)',
    'generative ai': 'Artificial Intelligence (AI)',
    'ml': 'Machine Learning (ML)', 'machine learning': 'Machine Learning (ML)',
    'devops': 'DevOps',
    'aws': 'AWS', 'amazon web services': 'AWS', 'gcp': 'Google Cloud Platform (GCP)',
    'google cloud': 'Google Cloud Platform (GCP)',
    'sql server': 'Microsoft SQL Server', 'ms sql': 'Microsoft SQL Server',
    'c sharp': '.NET / C#', 'c#': '.NET / C#', '.net': '.NET / C#',
    'cyber security': 'Cybersecurity', 'cybersecurity': 'Cybersecurity',
    'network security': 'Cybersecurity', 'tieng anh': 'English',
    'scrum agile': 'Agile & Scrum', 'agile scrum': 'Agile & Scrum',
    'project management': 'Project Management', 'quan ly du an': 'Project Management',
    'data analysis': 'Data Analysis', 'data analyst': 'Data Analysis',
    'automation rpa': 'Automation & RPA', 'rpa': 'Automation & RPA',
    'software testing': 'Software Testing', 'kiem thu phan mem': 'Software Testing',
    'restful api': 'API Development', 'rest api': 'API Development',
}

BOILERPLATE_PATTERN = re.compile(
    r'^\s*(?:Job description|Mô tả công việc|Your skills and experience|Yêu cầu công việc|'
    r'Job Description|Job Requirements|Requirements|What you[\'’]ll do|Responsibilities|'
    r'Yêu cầu ứng viên|Yêu cầu)[\s:\-–—]*',
    re.IGNORECASE
)

ATOMIC_SKILL_TAGS = {'ci/cd', 'c/c++', 'pl/sql', 'tcp/ip', 'qa/qc', 'ui/ux', '.net', '.net / c#'}


# ==============================================================================
# 1. TEXT CLEANING & NORMALIZATION
# ==============================================================================

def clean_text(v, is_jd: bool = False) -> str:
    """Clean HTML entities, remove boilerplate headers, and collapse excess whitespace."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).lower() in {'nan', 'none'}:
        return ''
    s = html.unescape(str(v).replace('\x00', ' '))
    if is_jd:
        s = BOILERPLATE_PATTERN.sub('', s)
        s = re.sub(r'^\s*(?:Job description|Mô tả công việc|Your skills and experience|Yêu cầu công việc)[\s:\-–—]*', '', s, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', s).strip()


def normalize(v: str) -> str:
    """ASCII folding, lowercasing, and special character normalization."""
    s = unicodedata.normalize('NFKD', clean_text(v).casefold().replace('đ', 'd'))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9+#.]+', ' ', s)).strip()


def normalize_city(raw_city: str) -> str:
    """Standardize city names to unified, accented Vietnamese names."""
    c = clean_text(raw_city)
    if not c:
        return 'Khác'
    norm = normalize(c)
    if any(k in norm for k in ['ha noi', 'hanoi', 'hn']):
        return 'Hà Nội'
    if any(k in norm for k in ['ho chi minh', 'hcm', 'sai gon', 'saigon', 'tp hcm', 'tp.hcm', 'thanh pho ho chi minh']):
        return 'Hồ Chí Minh'
    if 'da nang' in norm:
        return 'Đà Nẵng'
    if 'hai phong' in norm:
        return 'Hải Phòng'
    if 'can tho' in norm:
        return 'Cần Thơ'
    if 'binh duong' in norm:
        return 'Bình Dương'
    if 'dong nai' in norm:
        return 'Đồng Nai'
    if 'bac ninh' in norm:
        return 'Bắc Ninh'
    if 'ba ria' in norm or 'vung tau' in norm:
        return 'Bà Rịa - Vũng Tàu'
    if 'thai nguyen' in norm:
        return 'Thái Nguyên'
    if 'hung yen' in norm:
        return 'Hưng Yên'
    if 'ha tinh' in norm:
        return 'Hà Tĩnh'
    if 'vinh phuc' in norm:
        return 'Vĩnh Phúc'
    if 'tay ninh' in norm:
        return 'Tây Ninh'
    if 'ha nam' in norm:
        return 'Hà Nam'
    if 'hue' in norm or 'thua thien' in norm:
        return 'Thừa Thiên Huế'
    if 'long an' in norm:
        return 'Long An'
    if 'gia lai' in norm:
        return 'Gia Lai'
    if 'phu tho' in norm:
        return 'Phú Thọ'
    if 'ninh binh' in norm:
        return 'Ninh Bình'
    if 'thanh hoa' in norm:
        return 'Thanh Hóa'
    if 'quang ninh' in norm:
        return 'Quảng Ninh'
    if 'an giang' in norm:
        return 'An Giang'
    if 'ca mau' in norm:
        return 'Cà Mau'
    if 'thai binh' in norm:
        return 'Thái Bình'
    if 'quoc te' in norm or 'international' in norm:
        return 'Quốc tế'
    return c


def company_key(v: str) -> str:
    s = normalize(v)
    s = re.sub(r'(?<=\w)\.(?=\s|$)', ' ', s)
    s = COMPANY_STOP.sub(' ', s)
    return re.sub(r'\s+', ' ', s).strip() or normalize(v)


def _compact(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', company_key(name))


def _company_aliases(name: str) -> list[str]:
    n = clean_text(name)
    parts = re.split(r'\s+[|–—-]\s+', n)
    out = [parts[0], parts[-1]] if len(parts) > 1 else []
    return out + re.findall(r'\(([^()]{3,40})\)', n)


def split_skills(s: str) -> list[str]:
    """Parse skill tags, decomposing compound strings (e.g. 'Java/.Net/Python') into separate skills."""
    s = clean_text(s)
    if not s:
        return []
    raw_tokens = []
    if s.startswith('['):
        try:
            raw_tokens = [clean_text(k) for k in ast.literal_eval(s) if clean_text(k)]
        except (SyntaxError, ValueError):
            pass
    if not raw_tokens:
        raw_tokens = [v.strip() for v in re.split(r'\s*\|\s*|\s*;\s*', s) if v.strip()]

    # Decompose compound tokens like "Java/.Net/Python" while keeping atomic tags like "CI/CD" intact
    final_skills = []
    for tok in raw_tokens:
        low = tok.lower().strip()
        if low in ATOMIC_SKILL_TAGS:
            final_skills.append(tok)
            continue
        # Split on / if it looks like a list of distinct technologies
        if '/' in tok and not any(a in low for a in ['c/c++', 'ci/cd', 'pl/sql', 'tcp/ip', 'qa/qc', 'ui/ux']):
            parts = [p.strip() for p in tok.split('/') if p.strip()]
            if len(parts) > 1:
                final_skills.extend(parts)
                continue
        final_skills.append(tok)

    return final_skills


def deterministic_id(prefix: str, content: str) -> str:
    return prefix + hashlib.sha1(content.encode('utf-8')).hexdigest()[:12]


def title_key(s: str) -> str:
    s = normalize(s)
    return re.sub(r'\b(?:hn|hcm|hanoi|ha noi|ho chi minh|remote|onsite|urgent)\b', ' ', s).strip()


def parse_snapshot_date(filepath: str | Path) -> str | None:
    name = Path(filepath).name
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else None


# ==============================================================================
# 2. SNAPSHOT AGGREGATION & MASTER CREATION
# ==============================================================================

def build_itviec_master(snapshot_dir: Path, cutoff_date: str = "2026-10-25") -> pd.DataFrame:
    pattern = str(snapshot_dir / "*.csv")
    all_files = glob.glob(pattern)
    valid_files = []
    for f in all_files:
        d = parse_snapshot_date(f)
        if d and d <= cutoff_date:
            valid_files.append((d, f))

    valid_files.sort(key=lambda x: x[0])
    if not valid_files:
        raise FileNotFoundError(f"No ITViec snapshot files found <= {cutoff_date} in {snapshot_dir}")

    job_records: dict[str, dict] = {}
    job_first_seen: dict[str, str] = {}
    job_last_seen: dict[str, str] = {}
    job_seen_dates: dict[str, set[str]] = {}

    for s_date, fpath in valid_files:
        df = pd.read_csv(fpath, low_memory=False, dtype={"job_id": str})
        if "job_id" not in df.columns:
            continue
        df["job_id"] = df["job_id"].fillna("").astype(str).str.strip()
        df = df[df["job_id"] != ""]

        for _, row in df.iterrows():
            jid = str(row["job_id"])
            if jid not in job_first_seen:
                r_fs = str(row.get("first_seen", "")).strip()
                job_first_seen[jid] = r_fs if re.match(r"^\d{4}-\d{2}-\d{2}", r_fs) else s_date
                job_seen_dates[jid] = set()
            job_last_seen[jid] = s_date
            job_seen_dates[jid].add(s_date)

            rec = row.to_dict()
            rec["source_file"] = Path(fpath).name
            rec["site"] = "itviec"
            job_records[jid] = rec

    master_rows = []
    for jid, rec in job_records.items():
        fs = job_first_seen[jid]
        ls = job_last_seen[jid]
        try:
            days = (pd.to_datetime(ls) - pd.to_datetime(fs)).days + 1
        except Exception:
            days = len(job_seen_dates[jid])
        is_active = (ls == cutoff_date)

        text_len = len(clean_text(rec.get("description", ""))) + len(clean_text(rec.get("requirement", "")))
        rec["first_seen"] = fs
        rec["last_seen"] = ls
        rec["days_active"] = max(1, days)
        rec["is_active"] = is_active
        rec["left_censored"] = (fs <= "2026-10-11")
        rec["right_censored"] = is_active
        rec["text_source"] = "itviec_snapshot"
        rec["text_quality"] = "full" if text_len >= 400 else "truncated"
        rec["job_uid"] = f"itviec:{jid}"
        master_rows.append(rec)

    return pd.DataFrame(master_rows)


def build_vnworks_master(
    snapshot_dir: Path,
    cutoff_date: str = "2026-10-25",
    rich_file: Path | None = Path("vietnamworks_jobs.csv")
) -> pd.DataFrame:
    """Build VietnamWorks master dataset, enriching truncated JDs using vietnamworks_jobs.csv when available."""
    pattern = str(snapshot_dir / "*.csv")
    all_files = glob.glob(pattern)
    valid_files = []
    for f in all_files:
        d = parse_snapshot_date(f)
        if d and d <= cutoff_date:
            valid_files.append((d, f))

    valid_files.sort(key=lambda x: x[0])
    if not valid_files:
        raise FileNotFoundError(f"No VNWorks snapshot files found <= {cutoff_date} in {snapshot_dir}")

    job_records: dict[str, dict] = {}
    job_first_seen: dict[str, str] = {}
    job_last_seen: dict[str, str] = {}
    job_seen_dates: dict[str, set[str]] = {}

    for s_date, fpath in valid_files:
        df = pd.read_csv(fpath, low_memory=False, dtype={"job_id": str})
        if "job_id" not in df.columns:
            continue
        df["job_id"] = df["job_id"].fillna("").astype(str).str.strip()
        df = df[df["job_id"] != ""]

        for _, row in df.iterrows():
            jid = str(row["job_id"])
            if jid not in job_first_seen:
                r_fs = str(row.get("first_seen", "")).strip()
                job_first_seen[jid] = r_fs if re.match(r"^\d{4}-\d{2}-\d{2}", r_fs) else s_date
                job_seen_dates[jid] = set()
            job_last_seen[jid] = s_date
            job_seen_dates[jid].add(s_date)

            rec = row.to_dict()
            rec["source_file"] = Path(fpath).name
            rec["site"] = "vietnamworks"
            job_records[jid] = rec

    # Enrich from rich detailed crawl file if available
    rich_lookup = {}
    if rich_file and rich_file.exists():
        try:
            df_rich = pd.read_csv(rich_file, low_memory=False, dtype={"job_id": str})
            df_rich["job_id"] = df_rich["job_id"].fillna("").astype(str).str.strip()
            rich_lookup = {r["job_id"]: r for _, r in df_rich.iterrows() if r["job_id"]}
            print(f"-> Found {len(rich_lookup)} rich JDs in {rich_file.name} for enrichment.")
        except Exception as e:
            print(f"Warning: Could not load {rich_file}: {e}")

    enriched_count = 0
    master_rows = []
    for jid, rec in job_records.items():
        fs = job_first_seen[jid]
        ls = job_last_seen[jid]
        try:
            days = (pd.to_datetime(ls) - pd.to_datetime(fs)).days + 1
        except Exception:
            days = len(job_seen_dates[jid])
        is_active = (ls == cutoff_date)

        # Apply rich description and requirement if richer than snapshot snippet
        was_enriched = False
        if jid in rich_lookup:
            r_rec = rich_lookup[jid]
            r_desc = str(r_rec.get("description", "") or "")
            r_req = str(r_rec.get("requirement", "") or "")
            cur_desc = str(rec.get("description", "") or "")
            cur_req = str(rec.get("requirement", "") or "")

            if (len(r_desc) + len(r_req)) > (len(cur_desc) + len(cur_req)):
                rec["description"] = r_desc
                rec["requirement"] = r_req
                enriched_count += 1
                was_enriched = True
            if not rec.get("skills") and r_rec.get("skills"):
                rec["skills"] = r_rec.get("skills")
            if not rec.get("url") and r_rec.get("url"):
                rec["url"] = r_rec.get("url")

        text_len = len(clean_text(rec.get("description", ""))) + len(clean_text(rec.get("requirement", "")))
        rec["first_seen"] = fs
        rec["last_seen"] = ls
        rec["days_alive"] = max(1, days)
        rec["days_active"] = max(1, days)
        rec["is_active"] = is_active
        rec["left_censored"] = (fs <= "2026-10-11")
        rec["right_censored"] = is_active
        rec["text_source"] = "vietnamworks_enriched" if was_enriched else "vietnamworks_snapshot_truncated"
        rec["text_quality"] = "full" if (was_enriched and text_len >= 800) else "truncated"
        rec["status"] = "active" if is_active else "expired"
        rec["job_uid"] = f"vietnamworks:{jid}"
        master_rows.append(rec)

    print(f"-> Successfully enriched {enriched_count} VietnamWorks jobs with full JDs.")
    return pd.DataFrame(master_rows)


def harmonize_combine_masters(df_it: pd.DataFrame, df_vn: pd.DataFrame) -> pd.DataFrame:
    df_it_clean = df_it.copy()
    df_vn_clean = df_vn.copy()

    core_cols = [
        "job_uid", "site", "job_id", "title", "company", "city", "url",
        "salary_visible", "salary_min", "salary_max", "currency", "salary_period", "salary_text",
        "skills", "description", "requirement",
        "first_seen", "last_seen", "days_active", "is_active", "left_censored", "right_censored",
        "text_source", "text_quality", "source_file"
    ]

    for c in core_cols:
        if c not in df_it_clean.columns:
            df_it_clean[c] = None
        if c not in df_vn_clean.columns:
            df_vn_clean[c] = None

    combined = pd.concat([df_it_clean, df_vn_clean], ignore_index=True)
    other_cols = [c for c in combined.columns if c not in core_cols]
    final_cols = core_cols + sorted(other_cols)
    return combined[final_cols]


def join_cross_platform(df_it: pd.DataFrame, df_vn: pd.DataFrame) -> pd.DataFrame:
    it = df_it.copy()
    vn = df_vn.copy()

    it["c_norm"] = it["company"].fillna("").map(company_key)
    vn["c_norm"] = vn["company"].fillna("").map(company_key)
    it["t_norm"] = it["title"].fillna("").map(title_key)
    vn["t_norm"] = vn["title"].fillna("").map(title_key)

    ignore_companies = {"", "client", "anonymous", "confidential", "navigos search s client"}

    matched_pairs = []
    vn_by_comp: dict[str, list[dict]] = {}
    for _, r_vn in vn.iterrows():
        ck = r_vn["c_norm"]
        if ck and ck not in ignore_companies:
            vn_by_comp.setdefault(ck, []).append(r_vn.to_dict())

    for _, r_it in it.iterrows():
        ck = r_it["c_norm"]
        if not ck or ck in ignore_companies or ck not in vn_by_comp:
            continue

        cands = vn_by_comp[ck]
        for r_vn in cands:
            t_score = fuzzy_ratio(r_it["t_norm"], r_vn["t_norm"])
            if t_score >= 85:
                city_it = normalize(str(r_it.get("city", "")))
                city_vn = normalize(str(r_vn.get("city", "")))
                city_match = (
                    not city_it or not city_vn or
                    fuzzy_ratio(city_it, city_vn) >= 70 or
                    ("ha noi" in city_it and "ha noi" in city_vn) or
                    ("ho chi minh" in city_it and "ho chi minh" in city_vn) or
                    ("da nang" in city_it and "da nang" in city_vn)
                )

                jd_it = normalize(str(r_it.get("description", "")))[:2000]
                jd_vn = normalize(str(r_vn.get("description", "")))[:2000]
                jd_sim = fuzzy_ratio(jd_it, jd_vn) if len(jd_it) > 100 and len(jd_vn) > 100 else None

                matched_pairs.append({
                    "company_normalized": ck,
                    "company_itviec": r_it.get("company"),
                    "company_vnworks": r_vn.get("company"),
                    "title_itviec": r_it.get("title"),
                    "title_vnworks": r_vn.get("title"),
                    "title_similarity": round(t_score, 1),
                    "jd_similarity": round(jd_sim, 1) if jd_sim is not None else "N/A",
                    "city_itviec": r_it.get("city"),
                    "city_vnworks": r_vn.get("city"),
                    "salary_itviec": r_it.get("salary_text"),
                    "salary_vnworks": r_vn.get("salary_text"),
                    "skills_itviec": r_it.get("skills"),
                    "skills_vnworks": r_vn.get("skills"),
                    "first_seen_itviec": r_it.get("first_seen"),
                    "first_seen_vnworks": r_vn.get("first_seen"),
                    "last_seen_itviec": r_it.get("last_seen"),
                    "last_seen_vnworks": r_vn.get("last_seen"),
                    "itviec_job_uid": r_it.get("job_uid"),
                    "vnworks_job_uid": r_vn.get("job_uid"),
                    "url_itviec": r_it.get("url"),
                    "url_vnworks": r_vn.get("url"),
                })

    df_matches = pd.DataFrame(matched_pairs)
    return df_matches


def build_masters_and_join(
    itviec_dir: Path = Path("snapshotsitviec"),
    vnworks_dir: Path = Path("snapshotvnwork"),
    cutoff_date: str = "2026-10-25",
    rich_vnworks_file: Path | None = Path("vietnamworks_jobs.csv"),
    out_dir: Path = Path("hr_pipeline_output/master")
):
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== Aggregating Snapshots <= {cutoff_date} ===")

    df_it = build_itviec_master(itviec_dir, cutoff_date)
    it_file = out_dir / f"itviec_master_{cutoff_date}.csv"
    df_it.to_csv(it_file, index=False, encoding="utf-8-sig")
    print(f"-> Saved ITViec Master: {it_file.resolve()} ({len(df_it)} jobs)")

    df_vn = build_vnworks_master(vnworks_dir, cutoff_date, rich_file=rich_vnworks_file)
    vn_file = out_dir / f"vietnamworks_master_{cutoff_date}.csv"
    df_vn.to_csv(vn_file, index=False, encoding="utf-8-sig")
    print(f"-> Saved VNWorks Master: {vn_file.resolve()} ({len(df_vn)} jobs)")

    combined = harmonize_combine_masters(df_it, df_vn)
    combine_file = out_dir / f"combine_master_{cutoff_date}.csv"
    combined.to_csv(combine_file, index=False, encoding="utf-8-sig")
    print(f"-> Saved Combined Master: {combine_file.resolve()} ({len(combined)} jobs)")

    cross_matches = join_cross_platform(df_it, df_vn)
    match_file = out_dir / f"cross_platform_matched_{cutoff_date}.csv"
    cross_matches.to_csv(match_file, index=False, encoding="utf-8-sig")
    print(f"-> Saved Cross-Platform Joined Table: {match_file.resolve()} ({len(cross_matches)} matches)")

    return it_file, vn_file, combine_file, match_file


# ==============================================================================
# 3. COMPANY RESOLUTION
# ==============================================================================

def detect_companies(df: pd.DataFrame) -> dict[int, tuple[str, str, str]]:
    placeholders = {'client', 'anonymous', 'confidential'}
    names = [n for n in df.company.unique() if clean_text(n)]
    ck = {n: _compact(n) for n in names}
    parent = {k: k for k in set(ck.values()) if k}

    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for n in names:
        compact_n = ck[n]
        if not compact_n or compact_n in placeholders or 'navigosearch' in compact_n:
            continue
        for alias in _company_aliases(n):
            a = _compact(alias)
            if len(a) >= 4 and a in parent and a not in placeholders and 'navigosearch' not in a and a != compact_n:
                parent[root(compact_n)] = root(a)

    counts = Counter(df.company)
    members = defaultdict(list)
    for n in names:
        compact_n = ck[n]
        if compact_n and compact_n not in placeholders and 'navigosearch' not in compact_n:
            members[root(compact_n)].append(n)

    mapping_name = {}
    for r, ms in members.items():
        best = sorted(ms, key=lambda m: (-counts[m], len(clean_text(m)), clean_text(m)))[0]
        gid = deterministic_id('c_', r)
        for m in ms:
            mapping_name[m] = (gid, best, 'exact_normalized' if len(ms) == 1 else 'merged_variants')

    mapping = {}
    for i in df.index:
        comp_raw = clean_text(df.at[i, 'company'])
        comp_norm = normalize(comp_raw)
        if 'navigos search' in comp_norm:
            mapping[i] = ('c_navigos_client', "Navigos Search's Client (Confidential)", 'confidential_headhunter')
        elif comp_raw in mapping_name:
            mapping[i] = mapping_name[comp_raw]
        else:
            mapping[i] = (deterministic_id('c_unknown_', df.at[i, 'job_uid']), comp_raw or 'Unknown Company', 'unresolved')

    return mapping


# ==============================================================================
# 4. SALARY PARSING & STANDARDIZATION
# ==============================================================================

def parse_number(v: str) -> float:
    v = str(v).strip()
    if ',' in v and '.' in v:
        v = v.replace(',', '') if v.rfind('.') > v.rfind(',') else v.replace('.', '').replace(',', '.')
    elif '.' in v:
        if re.search(r'^\d{1,3}\.\d{3}$', v) or (re.search(r'\.\d{3}(?!\d)', v) and not re.search(r'\.\d{1,2}(?!\d)', v)):
            v = v.replace('.', '')
    elif ',' in v:
        if re.search(r',\d{3}(?:,|$)', v) or re.search(r'^\d{1,3},\d{3}$', v):
            v = v.replace(',', '')
        else:
            v = v.replace(',', '.')
    return float(v)


def extract_salary_from_title(title: str) -> dict | None:
    t = clean_text(title)
    if not t:
        return None

    # Range in title
    m_range = re.search(
        r'(?:thu nhập|lương|luong|salary)?\s*[:\-–]?\s*[\$]?\s*(\d[\d,.]*)\s*(?:tr|triệu|m|k|\$|usd)?\s*[-–—]\s*[\$]?\s*(\d[\d,.]*)\s*(tr|triệu|million|m\b|usd|\$|k\b)',
        t, re.IGNORECASE
    )
    if m_range:
        v1, v2, unit = m_range.group(1), m_range.group(2), m_range.group(3).lower()
        try:
            n1, n2 = parse_number(v1), parse_number(v2)
            if unit in {'tr', 'triệu', 'million', 'm'}:
                return {'salary_type': 'range', 'salary_min_m': n1, 'salary_max_m': n2, 'currency': 'VND', 'source': 'title'}
            elif unit in {'usd', '$'}:
                return {'salary_type': 'range', 'salary_min_m': round(n1 * USD_TO_VND / 1e6, 2),
                        'salary_max_m': round(n2 * USD_TO_VND / 1e6, 2), 'currency': 'USD', 'source': 'title'}
            elif unit == 'k':
                return {'salary_type': 'range', 'salary_min_m': round(n1 * 1000 * USD_TO_VND / 1e6, 2),
                        'salary_max_m': round(n2 * 1000 * USD_TO_VND / 1e6, 2), 'currency': 'USD', 'source': 'title'}
        except ValueError:
            pass

    # Up to in title
    m_up = re.search(
        r'\b(?:up\s*to|upto|tới|toi|đến|maximum|max)\s*[\$]?\s*(\d[\d,.]*)\s*(tr|triệu|million|m\b|usd|\$|k\b)?|'
        r'\b(\d[\d,.]*)\s*(tr|triệu|million|m\b|usd|\$)\s*(?:max|tối đa)\b',
        t, re.IGNORECASE
    )
    if m_up:
        num_str = m_up.group(1) or m_up.group(3)
        unit = (m_up.group(2) or m_up.group(4) or ('usd' if '$' in t else '')).lower()
        try:
            n = parse_number(num_str)
            if unit in {'tr', 'triệu', 'million', 'm'}:
                return {'salary_type': 'up_to', 'salary_min_m': None, 'salary_max_m': n, 'currency': 'VND', 'source': 'title'}
            elif unit in {'usd', '$'} or (500 <= n <= 10000 and '$' in t):
                return {'salary_type': 'up_to', 'salary_min_m': None,
                        'salary_max_m': round(n * USD_TO_VND / 1e6, 2), 'currency': 'USD', 'source': 'title'}
            elif unit == 'k':
                return {'salary_type': 'up_to', 'salary_min_m': None,
                        'salary_max_m': round(n * 1000 * USD_TO_VND / 1e6, 2), 'currency': 'USD', 'source': 'title'}
        except ValueError:
            pass

    return None


def salary_values(row: pd.Series) -> pd.Series:
    raw_text = clean_text(row.get('salary_text'))
    text = raw_text.lower()
    cur = clean_text(row.get('currency')).upper()
    period = clean_text(row.get('salary_period')).lower()

    # Tax type classification: Gross vs Net
    tax_type = 'net' if re.search(r'\bnet\b', text) else 'gross' if re.search(r'\bgross\b', text) else 'unspecified'

    # Reject non-salary text / company intro descriptions
    non_salary_cues = ['retail stores', 'omni-channel', 'wedding allowance', 'allowance:', 'stores in vietnam']
    if any(cue in text for cue in non_salary_cues) or (len(raw_text) > 80 and not re.search(r'\d\s*(?:tr|triệu|usd|\$|₫|vnd)', text)):
        return pd.Series({
            'salary_type': 'unknown', 'salary_min_m': None, 'salary_max_m': None,
            'salary_period_raw': period or 'month', 'salary_period_goc': period or 'month',
            'salary_currency_raw': cur, 'salary_currency_goc': cur,
            'salary_tax_type': tax_type,
            'salary_needs_review': False, 'salary_can_xem': False, 'salary_source': 'non_salary_rejected'
        })

    # Reject placeholder dummy salaries like "$ 1-1 /tháng"
    if re.search(r'^\s*[\$]?\s*1\s*[-–]\s*[12]\s*(?:/tháng|/month)?\s*$', text):
        return pd.Series({
            'salary_type': 'unknown', 'salary_min_m': None, 'salary_max_m': None,
            'salary_period_raw': period or 'month', 'salary_period_goc': period or 'month',
            'salary_currency_raw': cur, 'salary_currency_goc': cur,
            'salary_tax_type': tax_type,
            'salary_needs_review': False, 'salary_can_xem': False, 'salary_source': 'placeholder_rejected'
        })

    if not period:
        period = ('year' if re.search(r'/nam|/năm|per year|/year|/yr', text) else
                  'day' if re.search(r'/ngày|/day', text) else
                  'hour' if re.search(r'/giờ|/hour', text) else 'month')

    if re.search(r'\d\s*(?:tr|triệu)|tr\b|triệu', text):
        cur = 'VND'
    elif not cur:
        cur = 'USD' if ('$' in text or 'usd' in text) else 'VND' if re.search(r'₫|vnd', text) else ''

    negotiable = bool(re.search(r'thương lượng|thỏa thuận|thoả thuận|negotiable|competitive|confidential', text))
    upper = bool(re.search(r'\b(?:upto|up to|tới|toi|đến tối đa|maximum|max)\b', normalize(text)))
    lower = bool(re.search(r'\b(?:from|từ|tu|minimum|min|at least)\b', normalize(text))) or bool(re.search(r'\btừ\b|\bfrom\b', text))

    low = pd.to_numeric(row.get('salary_min'), errors='coerce')
    high = pd.to_numeric(row.get('salary_max'), errors='coerce')
    nums = re.findall(r'(?<!\w)\d[\d,.]*(?!\w)', text)

    if pd.isna(low) and pd.isna(high) and not negotiable and nums:
        try:
            values = [parse_number(n) for n in nums[:2]]
            low, high = (values[0], values[1]) if len(values) > 1 else (values[0], values[0])
        except ValueError:
            pass

    if pd.notna(low) and pd.isna(high) and not upper and not lower:
        lower = True
    if pd.isna(low) and pd.notna(high) and not upper and not lower:
        upper = True

    if upper:
        high = high if pd.notna(high) else low
        low = float('nan')
    elif lower:
        low = low if pd.notna(low) else high
        high = float('nan')

    if pd.notna(low) and pd.notna(high) and low > high:
        low, high = high, low

    typ = ('negotiable' if negotiable and pd.isna(low) and pd.isna(high) else
           'daily' if period == 'day' and (pd.notna(low) or pd.notna(high)) else
           'hourly' if period == 'hour' and (pd.notna(low) or pd.notna(high)) else
           'up_to' if upper else 'from' if lower else
           'range' if pd.notna(low) and pd.notna(high) and low != high else
           'exact' if pd.notna(low) or pd.notna(high) else
           'negotiable' if not text else 'unknown')

    factor = {'USD': USD_TO_VND / 1e6, 'VND': 1 / 1e6}.get(cur)
    if cur == 'VND' and re.search(r'\d\s*(?:tr|triệu)', text) and pd.notna(low) and low < 1000:
        factor = 1.0
    if cur == 'VND' and pd.notna(low) and low < 1000 and 'tr' not in text and 'triệu' not in text:
        factor = None

    month_factor = {'month': 1, 'year': 1 / 12, 'day': MONTHLY_WORKING_DAYS, 'hour': MONTHLY_WORKING_DAYS * 8}.get(period)
    if period in {'day', 'hour'} and not re.search(r'/ngày|/day|/giờ|/hour', text):
        month_factor = None

    ok = factor is not None and month_factor is not None
    mn = round(float(low) * factor * month_factor, 4) if ok and pd.notna(low) else None
    mx = round(float(high) * factor * month_factor, 4) if ok and pd.notna(high) else None

    # Fallback to Title
    sal_source = 'salary_text'
    if (mn is None and mx is None) or typ in {'negotiable', 'unknown'}:
        title_sal = extract_salary_from_title(row.get('title', ''))
        if title_sal:
            typ = title_sal['salary_type']
            mn = title_sal['salary_min_m']
            mx = title_sal['salary_max_m']
            cur = title_sal['currency']
            sal_source = 'title'

    # Check for suspicious high intern / fresher salary (> 30M VND / month)
    t_clean = normalize(clean_text(str(row.get('title', ''))))
    is_intern_or_fresher = bool(re.search(r'\b(?:intern|internship|thuc tap|thuc tap sinh|trainee|fresher)\b', t_clean))
    is_suspicious_intern_pay = is_intern_or_fresher and ((mn is not None and mn > 30.0) or (mx is not None and mx > 30.0))

    review = (not ok and (pd.notna(low) or pd.notna(high)) and sal_source == 'salary_text') or \
             any(v is not None and (v < 1 or v > 200) for v in (mn, mx)) or \
             bool(mn and mx and mx / mn > 5) or \
             is_suspicious_intern_pay

    if is_suspicious_intern_pay:
        sal_source = 'suspicious_intern_fresher_high_salary'

    return pd.Series({
        'salary_type': typ,
        'salary_min_m': mn,
        'salary_max_m': mx,
        'salary_period_raw': period,
        'salary_period_goc': period,
        'salary_currency_raw': cur,
        'salary_currency_goc': cur,
        'salary_tax_type': tax_type,
        'salary_needs_review': review,
        'salary_can_xem': review,
        'salary_source': sal_source
    })


def apply_manual_salary_fixes(df: pd.DataFrame, review_path: Path | None = None) -> pd.DataFrame:
    candidate_paths = [
        review_path,
        Path('manual_overrides/salary_review_filled.csv'),
        Path('da dien/salary_review_filled.csv')
    ]
    p = next((cp for cp in candidate_paths if cp and cp.exists()), None)
    if not p:
        return df

    try:
        rev_df = pd.read_csv(p)
    except Exception as e:
        print(f"Warning: Could not read {p}: {e}")
        return df

    fixes = rev_df[rev_df['decision'].isin(['apply_fix', 'set_null', 'keep_with_note'])].set_index('job_uid')
    for uid, r in fixes.iterrows():
        matches = df.index[df['job_uid'] == uid].tolist()
        if not matches:
            continue
        idx = matches[0]
        decision = r['decision']
        if decision == 'apply_fix':
            ft = str(r['fixed_type']).strip()
            if ft == 'from_min':
                ft = 'from'
            df.at[idx, 'salary_type_norm'] = ft
            df.at[idx, 'salary_min_m'] = pd.to_numeric(r['salary_min_m_fixed'], errors='coerce')
            df.at[idx, 'salary_max_m'] = pd.to_numeric(r['salary_max_m_fixed'], errors='coerce')
            df.at[idx, 'salary_can_xem'] = False
            df.at[idx, 'salary_needs_review'] = False
        elif decision == 'set_null':
            df.at[idx, 'salary_type_norm'] = 'unknown'
            df.at[idx, 'salary_min_m'] = None
            df.at[idx, 'salary_max_m'] = None
            df.at[idx, 'salary_can_xem'] = False
            df.at[idx, 'salary_needs_review'] = False
        elif decision == 'keep_with_note':
            df.at[idx, 'salary_can_xem'] = False
            df.at[idx, 'salary_needs_review'] = False

    return df


# ==============================================================================
# 5. SKILL TAXONOMY, ALIASES & CLASSIFICATION
# ==============================================================================

def make_skill_dictionary(
    reference: Path | None = None,
    taxonomy_file: Path | None = Path("manual_overrides/skill_taxonomy.csv"),
    alias_file: Path | None = Path("manual_overrides/skill_alias.csv")
):
    """Load canonical skills and alias mapping rules from taxonomy and alias files."""
    canon = set()
    lookup = defaultdict(list)
    taxonomy_meta = {}

    # 1. Load Taxonomy Metadata (family, category)
    if taxonomy_file and taxonomy_file.exists():
        try:
            tdf = pd.read_csv(taxonomy_file)
            for _, r in tdf.iterrows():
                sk = clean_text(r['skill'])
                if sk:
                    canon.add(sk)
                    taxonomy_meta[sk] = {
                        'skill_family': clean_text(r.get('skill_family', 'unknown')),
                        'skill_category': clean_text(r.get('skill_category', 'technical_hard_skill'))
                    }
                    lookup[normalize(sk)] = [sk]
        except Exception as e:
            print(f"Warning: Could not load taxonomy {taxonomy_file}: {e}")

    # 2. Load Alias Mapping Rules
    if alias_file and alias_file.exists():
        try:
            adf = pd.read_csv(alias_file)
            for _, r in adf.iterrows():
                raw = clean_text(r['alias_pattern'])
                c_str = clean_text(r['canonical_skills'])
                needs_chk = bool(r.get('needs_human_check', False))
                conf = clean_text(r.get('confidence', 'high'))
                canon_items = [c.strip() for c in re.split(r'[,|;]', c_str) if c.strip()]
                if raw and canon_items:
                    for item in canon_items:
                        canon.add(item)
                    key = normalize(raw)
                    lookup[key] = canon_items
        except Exception as e:
            print(f"Warning: Could not load alias file {alias_file}: {e}")

    # Fallback to filled review file if alias file was missing
    if not lookup:
        fallback_paths = [Path("manual_overrides/skill_review_filled.csv"), Path("da dien/skill_review_filled.csv")]
        fb = next((p for p in fallback_paths if p.exists()), None)
        if fb:
            try:
                rf = pd.read_csv(fb)
                mapped = rf[rf['decision'] == 'map']
                for _, r in mapped.iterrows():
                    raw = clean_text(r['skill_raw'])
                    c_single = clean_text(r.get('skill_canonical', ''))
                    c_all = clean_text(r.get('skill_canonical_all', ''))
                    canon_items = [c.strip() for c in re.split(r'[,|;]', c_all or c_single) if c.strip()]
                    if canon_items:
                        for item in canon_items:
                            canon.add(item)
                        lookup[normalize(raw)] = canon_items
            except Exception:
                pass

    # Built-in aliases
    for a, target in SKILL_ALIASES.items():
        canon.add(target)
        k = normalize(a)
        if k not in lookup:
            lookup[k] = [target]
        elif target not in lookup[k]:
            lookup[k].append(target)

    for c in list(canon):
        k = normalize(c)
        if k not in lookup:
            lookup[k] = [c]

    return canon, lookup, taxonomy_meta


def skill_match(raw: str, canon: set, lookup: dict) -> tuple[list[str], str]:
    key = normalize(raw)
    if key in lookup:
        return list(lookup[key]), 'exact_or_alias'
    return [], 'unmapped_review'


# ==============================================================================
# 6. DEDUPLICATION & TIME HARMONIZATION
# ==============================================================================

def text_containment(text_a: str, text_b: str) -> float:
    toks_a = [w for w in re.split(r'\W+', str(text_a).lower()) if w]
    toks_b = [w for w in re.split(r'\W+', str(text_b).lower()) if w]
    if not toks_a or not toks_b:
        return 0.0
    shorter, longer = (toks_a, set(toks_b)) if len(toks_a) <= len(toks_b) else (toks_b, set(toks_a))
    matched = sum(1 for w in shorter if w in longer)
    return round(matched / len(shorter) * 100, 1)


def deduplicate(
    df: pd.DataFrame,
    dup_override_path: Path | None = None,
    audit_sample_path: Path | None = Path("hr_pipeline_output/clean/duplicate_audit_sample_20.csv")
):
    """Clustering deduplication matching on company + title + city with strict guard rule:
    Only merges if text_containment >= 90% and minimum experience matches.
    Prevents transitive chaining and backfills salary to primary when missing.
    Harmonizes timeline across duplicates: min(first_seen), max(last_seen), any(is_active).
    Exports a 20-pair sample audit table for human verification.
    """
    buckets = defaultdict(list)
    for i, row in df.iterrows():
        if row['company_match_status'] != 'unresolved':
            c_id = row['company_canonical_id']
            city_norm = normalize_city(row.get('city', ''))
            buckets[(c_id, city_norm)].append(i)

    posted = {}
    for i in df.index:
        row = df.loc[i]
        ts = float('inf')
        for col in ('posted_date', 'posted_on', 'first_seen'):
            v = pd.to_datetime(row.get(col), errors='coerce', utc=True)
            if pd.notna(v):
                ts = v.value
                break
        posted[i] = ts

    tkey = {i: title_key(df.at[i, 'title']) for i in df.index}
    raw_text = {i: (str(df.at[i, 'description']) + ' ' + str(df.at[i, 'requirement'])) for i in df.index}
    jd_text = {i: normalize(raw_text[i])[:3000] for i in df.index}
    exp_vals = {i: df.at[i, 'exp_min_years'] for i in df.index}

    parent = list(range(len(df)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    reviews = []
    auto_clustered_pairs = []

    for (c_id, _), ids in buckets.items():
        if len(ids) < 2:
            continue
        for pos, i in enumerate(ids):
            for j in ids[pos + 1:]:
                a, b = df.loc[i], df.loc[j]
                title_sim = fuzzy_ratio(tkey[i], tkey[j])
                loc_sim = fuzzy_ratio(normalize(str(a.get('city', ''))), normalize(str(b.get('city', '')))) if a.get('city') and b.get('city') else 100
                jd_sim = fuzzy_ratio(jd_text[i], jd_text[j]) if len(jd_text[i]) > 100 and len(jd_text[j]) > 100 else 0

                containment = text_containment(raw_text[i], raw_text[j])
                exp_i, exp_j = exp_vals[i], exp_vals[j]
                same_exp = pd.isna(exp_i) or pd.isna(exp_j) or exp_i == exp_j
                guard_pass = (containment >= 90.0) and same_exp

                if title_sim >= 90:
                    if guard_pass:
                        parent[root(j)] = root(i)
                        auto_clustered_pairs.append({
                            'job_uid_1': a.job_uid, 'job_uid_2': b.job_uid,
                            'company': a.company,
                            'title_1': a.title, 'title_2': b.title,
                            'city': a.city,
                            'title_similarity': round(title_sim, 1),
                            'jd_similarity': round(jd_sim, 1),
                            'text_overlap_pct': containment,
                            'same_exp_or_unknown': same_exp,
                            'proposed_guard_pass': True,
                            'rule': 'company_city_title_sim_90'
                        })
                    else:
                        reviews.append({
                            'job_uid_1': a.job_uid, 'job_uid_2': b.job_uid,
                            'title_similarity': round(title_sim, 1), 'jd_similarity': round(jd_sim, 1),
                            'text_overlap_pct': containment,
                            'same_exp_or_unknown': same_exp,
                            'proposed_guard_pass': False,
                            'reason': 'rejected_by_containment_or_exp_guard'
                        })
                elif title_sim >= 85 and jd_sim >= 60:
                    if guard_pass:
                        parent[root(j)] = root(i)
                        auto_clustered_pairs.append({
                            'job_uid_1': a.job_uid, 'job_uid_2': b.job_uid,
                            'company': a.company,
                            'title_1': a.title, 'title_2': b.title,
                            'city': a.city,
                            'title_similarity': round(title_sim, 1),
                            'jd_similarity': round(jd_sim, 1),
                            'text_overlap_pct': containment,
                            'same_exp_or_unknown': same_exp,
                            'proposed_guard_pass': True,
                            'rule': 'company_city_title_85_jd_60'
                        })
                    else:
                        reviews.append({
                            'job_uid_1': a.job_uid, 'job_uid_2': b.job_uid,
                            'title_similarity': round(title_sim, 1), 'jd_similarity': round(jd_sim, 1),
                            'text_overlap_pct': containment,
                            'same_exp_or_unknown': same_exp,
                            'proposed_guard_pass': False,
                            'reason': 'rejected_by_containment_or_exp_guard'
                        })
                elif title_sim >= 80 and jd_sim >= 50:
                    reviews.append({
                        'job_uid_1': a.job_uid, 'job_uid_2': b.job_uid,
                        'title_similarity': round(title_sim, 1), 'jd_similarity': round(jd_sim, 1),
                        'city_similarity': round(loc_sim, 1),
                        'text_overlap_pct': containment,
                        'same_exp_or_unknown': same_exp,
                        'proposed_guard_pass': False,
                        'reason': 'possible_duplicate_manual_review'
                    })

    # Apply manual review overrides & audit sample decisions
    candidate_paths = [
        dup_override_path,
        Path('manual_overrides/duplicate_audit_sample_20_filled.csv'),
        Path('duplicate_audit_sample_20_filled.csv'),
        Path('manual_overrides/duplicate_review_filled.csv'),
        Path('da dien/duplicate_review_filled.csv')
    ]
    uid_to_idx = {df.at[i, 'job_uid']: i for i in df.index}
    confirmed_dup_pairs = set()
    forbidden_pairs = set()

    for p in candidate_paths:
        if not p or not p.exists():
            continue
        try:
            m_dup = pd.read_csv(p)
            for _, r in m_dup.iterrows():
                decision = str(r.get('decision', '') or r.get('audit_decision', '')).strip()
                k_uid = str(r.get('keep_uid', '') or r.get('job_uid_1', '')).strip()
                d_uid = str(r.get('drop_uid', '') or r.get('job_uid_2', '')).strip()
                if not k_uid or not d_uid:
                    continue
                pair_key = tuple(sorted([k_uid, d_uid]))
                if decision == 'duplicate':
                    confirmed_dup_pairs.add(pair_key)
                    if k_uid in uid_to_idx and d_uid in uid_to_idx:
                        k_idx, d_idx = uid_to_idx[k_uid], uid_to_idx[d_uid]
                        parent[root(d_idx)] = root(k_idx)
                elif decision in {'keep_both', 'not_duplicate'}:
                    forbidden_pairs.add(pair_key)
        except Exception as e:
            print(f"Warning: Could not apply duplicate review overrides from {p}: {e}")

    # Build preliminary clusters
    raw_clusters = defaultdict(list)
    for i in df.index:
        raw_clusters[root(i)].append(i)

    # Validate clusters against primary and guard rule to strictly prevent transitive chaining
    clusters = defaultdict(list)
    for root_id, member_ids in raw_clusters.items():
        if len(member_ids) <= 1:
            clusters[root_id] = member_ids
            continue

        def rank_candidate(i):
            is_itviec = 0 if df.at[i, 'site'] == 'itviec' else 1
            text_len = len(clean_text(df.at[i, 'requirement'])) + len(clean_text(df.at[i, 'description']))
            return (is_itviec, -text_len, posted[i], df.at[i, 'job_uid'])

        sorted_m = sorted(member_ids, key=rank_candidate)
        main_cand = sorted_m[0]
        verified_members = [main_cand]

        for other in sorted_m[1:]:
            u_main, u_other = df.at[main_cand, 'job_uid'], df.at[other, 'job_uid']
            pair_key = tuple(sorted([u_main, u_other]))
            if pair_key in forbidden_pairs:
                clusters[other] = [other]
                continue

            c = text_containment(raw_text[main_cand], raw_text[other])
            exp_m, exp_o = exp_vals[main_cand], exp_vals[other]
            s_exp = pd.isna(exp_m) or pd.isna(exp_o) or exp_m == exp_o

            # Guard rule or confirmed duplicate
            if (c >= 90.0 and s_exp) or pair_key in confirmed_dup_pairs:
                verified_members.append(other)
            else:
                # Transitive chaining broken: split off
                clusters[other] = [other]

        clusters[root_id] = verified_members

    fields = {
        'is_duplicate': [False] * len(df),
        'duplicate_group_id': [''] * len(df),
        'nhom_trung': [''] * len(df),
        'duplicate_role': [''] * len(df),
        'vai_tro_trung': [''] * len(df),
        'duplicate_of_uid': [''] * len(df),
        'trung_voi_job_uid': [''] * len(df),
        'n_postings_in_group': [1] * len(df),
        'duplicate_copies_count': [0] * len(df),
        'so_ban_sao': [0] * len(df),
        'is_salary_inconsistent': [False] * len(df),
        'is_change_salary': [False] * len(df)
    }

    # Harmonize timeline, postings count & backfill salary to primary when missing
    for ids in clusters.values():
        if len(ids) < 2:
            continue

        def rank_key(i):
            is_itviec = 0 if df.at[i, 'site'] == 'itviec' else 1
            text_len = len(clean_text(df.at[i, 'requirement'])) + len(clean_text(df.at[i, 'description']))
            return (is_itviec, -text_len, posted[i], df.at[i, 'job_uid'])

        ids = sorted(ids, key=rank_key)
        main = ids[0]
        group_key = deterministic_id('g_', '|'.join(sorted(df.at[i, 'job_uid'] for i in ids)))

        # Time harmonization
        all_fs = [df.at[i, 'first_seen'] for i in ids if clean_text(df.at[i, 'first_seen'])]
        all_ls = [df.at[i, 'last_seen'] for i in ids if clean_text(df.at[i, 'last_seen'])]
        any_active = any(bool(df.at[i, 'is_active']) for i in ids)

        min_fs = min(all_fs) if all_fs else df.at[main, 'first_seen']
        max_ls = max(all_ls) if all_ls else df.at[main, 'last_seen']

        # Update primary with harmonized dates
        df.at[main, 'first_seen'] = min_fs
        df.at[main, 'last_seen'] = max_ls
        df.at[main, 'is_active'] = any_active
        try:
            df.at[main, 'days_active'] = max(1, (pd.to_datetime(max_ls) - pd.to_datetime(min_fs)).days + 1)
        except Exception:
            pass

        # Backfill salary from duplicate member if primary lacks salary
        primary_has_sal = (
            df.at[main, 'salary_type_norm'] not in {'unknown', 'negotiable', ''}
            and (pd.notna(df.at[main, 'salary_min_m']) or pd.notna(df.at[main, 'salary_max_m']))
        )
        if not primary_has_sal:
            dup_with_sal = next(
                (i for i in ids if i != main and df.at[i, 'salary_type_norm'] not in {'unknown', 'negotiable', ''}
                 and (pd.notna(df.at[i, 'salary_min_m']) or pd.notna(df.at[i, 'salary_max_m']))),
                None
            )
            if dup_with_sal is not None:
                df.at[main, 'salary_type_norm'] = df.at[dup_with_sal, 'salary_type_norm']
                df.at[main, 'salary_min_m'] = df.at[dup_with_sal, 'salary_min_m']
                df.at[main, 'salary_max_m'] = df.at[dup_with_sal, 'salary_max_m']
                df.at[main, 'salary_currency_raw'] = df.at[dup_with_sal, 'salary_currency_raw']
                df.at[main, 'salary_currency_goc'] = df.at[dup_with_sal, 'salary_currency_goc']
                df.at[main, 'salary_tax_type'] = df.at[dup_with_sal, 'salary_tax_type']
                df.at[main, 'salary_period_raw'] = df.at[dup_with_sal, 'salary_period_raw']
                df.at[main, 'salary_period_goc'] = df.at[dup_with_sal, 'salary_period_goc']
                df.at[main, 'salary_source'] = 'backfilled_from_duplicate'

        sigs = {(df.at[i, 'salary_min_m'], df.at[i, 'salary_max_m']) for i in ids}
        salary_inconsistent = len(sigs) > 1

        for i in ids:
            is_dup = (i != main)
            fields['duplicate_group_id'][i] = group_key
            fields['nhom_trung'][i] = group_key
            fields['duplicate_role'][i] = 'primary' if not is_dup else 'duplicate'
            fields['vai_tro_trung'][i] = 'ban_chinh' if not is_dup else 'ban_sao'
            fields['duplicate_of_uid'][i] = '' if not is_dup else df.at[main, 'job_uid']
            fields['trung_voi_job_uid'][i] = '' if not is_dup else df.at[main, 'job_uid']
            fields['n_postings_in_group'][i] = len(ids)
            fields['is_duplicate'][i] = is_dup
            fields['duplicate_copies_count'][i] = len(ids) - 1 if not is_dup else 0
            fields['so_ban_sao'][i] = len(ids) - 1 if not is_dup else 0
            fields['is_salary_inconsistent'][i] = salary_inconsistent
            fields['is_change_salary'][i] = salary_inconsistent

    # Export a 20-pair sample audit table for human spot-check
    if audit_sample_path and auto_clustered_pairs:
        audit_sample_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(auto_clustered_pairs[:20]).to_csv(audit_sample_path, index=False, encoding='utf-8-sig')

    return fields, pd.DataFrame(reviews)


# ==============================================================================
# 7. MAIN PIPELINE EXECUTION
# ==============================================================================

def run(inputs=None, reference=None, out=Path('hr_pipeline_output'),
        from_snapshots=True, itviec_dir=Path('snapshotsitviec'),
        vnworks_dir=Path('snapshotvnwork'), cutoff='2026-10-25',
        rich_vnworks_file=Path('vietnamworks_jobs.csv')):
    """Execute end-to-end cleaning, skill scoring, and dashboard mart creation."""
    out = Path(out)
    clean_dir = out if out.name == 'clean' else out / 'clean'
    master_dir = out.parent / 'master' if out.name == 'clean' else out / 'master'

    if from_snapshots or not inputs:
        it_file, vn_file, _, _ = build_masters_and_join(
            itviec_dir=itviec_dir,
            vnworks_dir=vnworks_dir,
            cutoff_date=cutoff,
            rich_vnworks_file=rich_vnworks_file,
            out_dir=master_dir
        )
        inputs = [it_file, vn_file]

    frames = []
    for path in inputs:
        p = Path(path)
        raw = pd.read_csv(p, low_memory=False, dtype={'job_id': str}) if p.suffix.lower() == '.csv' else pd.read_excel(p, dtype={'job_id': str})
        if 'job_id' not in raw or 'site' not in raw:
            raise ValueError(f'{p}: missing job_id/site')
        raw['source_file'] = p.name
        frames.append(raw)

    df = pd.concat(frames, ignore_index=True)
    df['site'] = df['site'].fillna('').map(lambda x: normalize(x).replace(' ', ''))
    df['job_id'] = df.job_id.fillna('').astype(str).str.strip()
    df['job_uid'] = df.site + ':' + df.job_id

    same_id = df[df.job_uid.duplicated(keep=False)].copy()
    df = df.drop_duplicates('job_uid', keep='last').reset_index(drop=True)

    # 1. Text & City Cleaning
    print("--- Cleaning text, HTML entities, boilerplate, and normalizing cities ---")
    df['title'] = df['title'].fillna('').map(lambda s: clean_text(s))
    df['company'] = df['company'].fillna('').map(lambda s: clean_text(s))
    df['city'] = df['city'].fillna('').map(normalize_city)
    df['description'] = df['description'].fillna('').map(lambda s: clean_text(s, is_jd=True))
    df['requirement'] = df['requirement'].fillna('').map(lambda s: clean_text(s, is_jd=True))
    df['salary_text'] = df['salary_text'].fillna('').map(lambda s: clean_text(s))
    df['skills'] = df['skills'].fillna('').astype(str)

    # Text source & quality assessment
    if 'text_source' not in df.columns:
        df['text_source'] = ['itviec_snapshot' if s == 'itviec' else 'vietnamworks_snapshot_truncated' for s in df['site']]
    text_lengths = df['description'].str.len() + df['requirement'].str.len()
    # ITViec >= 400 is full; VietnamWorks only enriched and >= 800 is full
    df['text_quality'] = [
        'full' if (s == 'itviec' and l >= 400) or (src == 'vietnamworks_enriched' and l >= 800) else 'truncated'
        for s, src, l in zip(df['site'], df['text_source'], text_lengths)
    ]

    # Left & Right Censoring flags
    df['left_censored'] = df['first_seen'].fillna('').map(lambda d: str(d) <= '2026-10-11')
    if 'right_censored' not in df.columns:
        df['right_censored'] = df['is_active'].fillna(False).astype(bool)

    df['stt'] = range(1, len(df) + 1)

    # 2. Company Resolution
    print("--- Resolving canonical companies ---")
    companies = detect_companies(df)
    df['company_canonical_id'] = [companies[i][0] for i in df.index]
    df['company_canonical_name'] = [companies[i][1] for i in df.index]
    df['company_match_status'] = [companies[i][2] for i in df.index]

    # 3. Salary Parsing & Manual Overrides
    print("--- Parsing salaries and applying curated corrections ---")
    salary = df.apply(salary_values, axis=1)
    salary = salary.rename(columns={'salary_type': 'salary_type_norm'})
    df = pd.concat([df, salary], axis=1)

    df = apply_manual_salary_fixes(df)

    # 4. Skill Dictionary Loading & Extraction
    print("--- Mapping skills with 2-tier taxonomy & alias rules ---")
    canon, lookup, taxonomy_meta = make_skill_dictionary(reference)
    aliases_by_skill = defaultdict(list)
    for key, vals in lookup.items():
        if len(vals) == 1 and 3 <= len(key) <= 40:
            aliases_by_skill[vals[0]].append(key)

    skill_rows, skill_level_rows, unmapped = [], [], Counter()
    skills_by_job = {}

    for r in df.itertuples(index=False):
        matched = set()
        seen_labels = set()
        source_row = {'requirement': r.requirement, 'description': r.description}
        for tag in split_skills(r.skills):
            values, status = skill_match(tag, canon, lookup)
            if not values:
                unmapped[tag] += 1
                skill_rows.append({
                    'job_uid': r.job_uid, 'skill_raw': tag, 'skill_canonical': '',
                    'skill_family': 'unknown', 'skill_category': 'unknown',
                    'mapping_status': status, 'needs_human_check': True,
                    **classify_skill(source_row, tag, '')
                })
                continue
            for value in values:
                matched.add(value)
                meta = taxonomy_meta.get(value, {'skill_family': 'technical', 'skill_category': 'technical_hard_skill'})
                scoring = classify_skill(source_row, tag, value, aliases_by_skill.get(value, ()))
                needs_chk = scoring.get('skill_needs_review', False) or (meta['skill_category'] == 'unknown')

                skill_entry = {
                    'job_uid': r.job_uid, 'skill_raw': tag, 'skill_canonical': value,
                    'skill_family': meta['skill_family'], 'skill_category': meta['skill_category'],
                    'mapping_status': status, 'needs_human_check': needs_chk,
                    **scoring
                }
                skill_rows.append(skill_entry)

                if value not in seen_labels:
                    seen_labels.add(value)
                    skill_level_rows.append({
                        'job_uid': r.job_uid, 'stt': r.stt,
                        'skill': value, 'skill_raw': tag,
                        'skill_family': meta['skill_family'], 'skill_category': meta['skill_category'],
                        'needs_human_check': needs_chk,
                        **scoring
                    })
        skills_by_job[r.job_uid] = sorted(matched)

    df['skills_canonical_list'] = df.job_uid.map(lambda u: json.dumps(skills_by_job[u], ensure_ascii=False))
    df['skills_list_normalize'] = df['skills_canonical_list']

    # 5. Experience & Level
    print("--- Extracting experience & job level ---")
    exp = df.apply(lambda r: pd.Series(extract_experience(r)), axis=1)
    df = pd.concat([df, exp], axis=1)

    job_levels = df.apply(lambda r: extract_level(r, r['exp_min_years'] if pd.notna(r['exp_min_years']) else None), axis=1)
    df['level_norm'] = [v[0] for v in job_levels]
    df['level_source'] = [v[1] for v in job_levels]
    df['level_needs_review'] = [v[2] for v in job_levels]
    df['level_can_xem'] = df['level_needs_review']
    df['level_inferred_exp'] = [infer_level_from_experience(e if pd.notna(e) else None) if lv == 'unknown' else ''
                                for e, lv in zip(df.exp_min_years, df.level_norm)]

    # 6. Deduplication & Time Harmonization
    print("--- Running enhanced deduplication & time harmonization ---")
    dup, review = deduplicate(df, audit_sample_path=clean_dir / 'duplicate_audit_sample_20.csv')
    for k, v in dup.items():
        df[k] = v

    df['valid_job'] = ~df['is_duplicate']
    df['is_valid'] = df['valid_job']
    df['hop_le'] = df['valid_job']

    # 7. Job Skill Level Aggregation
    level_df = pd.DataFrame(skill_level_rows)
    if not level_df.empty:
        enrich = df.set_index('job_uid')[['level_norm', 'is_duplicate', 'hop_le']]
        level_df = level_df.join(enrich, on='job_uid')
        level_df['role_group'] = 'unknown'
        skill_summary = level_df.groupby('job_uid').apply(
            lambda g: pd.Series({
                'skills_required': '|'.join(sorted(g.loc[g.importance == 'required', 'skill'].unique())),
                'skills_preferred': '|'.join(sorted(g.loc[g.importance == 'preferred', 'skill'].unique())),
                'skills_advanced': '|'.join(sorted(g.loc[g.proficiency == 'advanced', 'skill'].unique()))
            }), include_groups=False)
        df = df.join(skill_summary, on='job_uid')

    # Date normalization
    for col in ['posted_date', 'posted_on', 'posted_first', 'expired_on', 'expired_date', 'first_seen', 'last_seen']:
        if col in df:
            df[col] = pd.to_datetime(df[col], errors='coerce', utc=True).dt.strftime('%Y-%m-%d')
    if 'posted_on' in df:
        df['posted_date'] = df.get('posted_date', pd.Series(index=df.index, dtype='object')).fillna(df['posted_on'])
    if 'expired_on' in df:
        df['expired_date'] = df.get('expired_date', pd.Series(index=df.index, dtype='object')).fillna(df['expired_on'])

    # 8. Drop constant/empty columns and corrupted crawler columns
    cols_to_drop = [
        'gone_on', 'end_reason', 'salary_exchange_rate',
        'salary_min_mvnd_month', 'salary_max_mvnd_month', 'salary_mid_mvnd_month'
    ]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    # 9. Invariants Check
    assert df['job_uid'].is_unique, "Invariant violation: job_uid must be unique across all records!"
    range_jobs = df[df['salary_type_norm'].isin(['range', 'exact']) & df['salary_min_m'].notna() & df['salary_max_m'].notna()]
    assert (range_jobs['salary_min_m'] <= range_jobs['salary_max_m']).all(), "Invariant violation: salary_min_m must be <= salary_max_m!"

    # 10. Save Clean Outputs
    clean_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(clean_dir / 'combine_clean.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(skill_rows).to_csv(clean_dir / 'job_skill_map.csv', index=False, encoding='utf-8-sig')
    level_df.to_csv(clean_dir / 'job_skill_level.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame([{'skill_raw': a, 'count': b} for a, b in unmapped.most_common()]).to_csv(clean_dir / 'skill_review.csv', index=False, encoding='utf-8-sig')
    review.to_csv(clean_dir / 'duplicate_review.csv', index=False, encoding='utf-8-sig')
    same_id.to_csv(clean_dir / 'repeated_source_ids.csv', index=False, encoding='utf-8-sig')

    companies_out = df[['company', 'company_canonical_id', 'company_canonical_name', 'company_match_status']].drop_duplicates()
    companies_out.to_csv(clean_dir / 'company_map.csv', index=False, encoding='utf-8-sig')

    stats = {
        'input_rows': sum(len(x) for x in frames),
        'unique_job_uids': len(df),
        'source_duplicate_rows': len(same_id),
        'duplicate_jobs': int(df.is_duplicate.sum()),
        'deduplicated_unique_jobs': int(df.valid_job.sum()),
        'duplicate_review_pairs': len(review),
        'company_ids': df.company_canonical_id.nunique(),
        'skill_tags': len(skill_rows),
        'unmapped_skill_tags': sum(unmapped.values()),
        'job_skill_level_rows': len(level_df),
        'skill_required': int((level_df.importance == 'required').sum()),
        'skill_preferred': int((level_df.importance == 'preferred').sum()),
        'skill_duty': int((level_df.importance == 'duty').sum()),
        'skill_listed_only': int((level_df.importance == 'listed_only').sum()),
        'exp_extracted_jobs': int(df.exp_min_years.notna().sum()),
        'level_identified_jobs': int((df.level_norm != 'unknown').sum()),
        'salary_comparable_jobs': int(df.salary_min_m.notna().sum()),
        'text_quality_full_jobs': int((df.text_quality == 'full').sum()),
        'text_quality_truncated_jobs': int((df.text_quality == 'truncated').sum()),
        'left_censored_jobs': int(df.left_censored.sum()),
        'right_censored_jobs': int(df.right_censored.sum()) if 'right_censored' in df.columns else 0,
        'text_source_counts': df['text_source'].value_counts().to_dict() if 'text_source' in df.columns else {},
        'reference_skill_labels': len(canon),
        'assumptions': {
            'monthly_working_days': MONTHLY_WORKING_DAYS,
            'usd_vnd_rate': USD_TO_VND,
            'observation_window_days': 15,
            'left_censored_boundary': '2026-10-11',
            'right_censored_boundary': '2026-10-25 (is_active)'
        },
        'input_sources': [Path(p).name for p in inputs]
    }
    (clean_dir / 'quality_report.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
    print("=== Quality Report Summary ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return clean_dir


if __name__ == '__main__':
    p = argparse.ArgumentParser(description="Recruitment data cleaning & scoring pipeline")
    p.add_argument('--input', nargs='+', type=Path, help="Explicit master CSV files")
    p.add_argument('--from-snapshots', action='store_true', default=False, help="Aggregate from daily snapshots")
    p.add_argument('--itviec-dir', type=Path, default=Path('snapshotsitviec'), help="ITViec snapshots directory")
    p.add_argument('--vnworks-dir', type=Path, default=Path('snapshotvnwork'), help="VietnamWorks snapshots directory")
    p.add_argument('--cutoff', type=str, default='2026-10-25', help="Snapshot cutoff date (YYYY-MM-DD)")
    p.add_argument('--reference', type=Path, help="Canonical skills workbook")
    p.add_argument('--out', type=Path, default=Path('hr_pipeline_output'), help="Output directory")
    a = p.parse_args()

    run(inputs=a.input, reference=a.reference, out=a.out,
        from_snapshots=a.from_snapshots or not a.input,
        itviec_dir=a.itviec_dir, vnworks_dir=a.vnworks_dir, cutoff=a.cutoff)
