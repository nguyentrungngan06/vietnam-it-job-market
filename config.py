"""
Cấu hình tập trung cho hệ thống Crawler ITviec.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# File paths
AUTH_FILE = os.path.join(BASE_DIR, "auth.json")
MASTER_FILE = os.path.join(BASE_DIR, "itviec_master.csv")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
CRAWL_LOG_FILE = os.path.join(BASE_DIR, "crawl_log.csv")
DEDUP_MAP_FILE = os.path.join(BASE_DIR, "job_dedup_mapping.csv")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "checkpoint_crawl_today.csv")

# Danh sách cột chuẩn hóa trong file Master
ORDERED_COLS = [
    "job_id",
    "title",
    "company",
    "company_slug",
    "url",
    "city",
    "level",
    "work_mode",
    "company_type",
    "company_size",
    "company_size_range",
    "posted_date",
    "salary_visible",
    "has_salary",
    "salary_min",
    "salary_max",
    "currency",
    "salary_text",
    "salary_type",
    "salary_from_text",
    "skills",
    "description",
    "requirement",
    "site",
    "job_key",
    "first_seen",
    "last_seen",
    "days_active",
    "is_active",
    "is_duplicate",
    "canonical_job_key",
]

SALARY_COLS = [
    "salary_visible",
    "salary_min",
    "salary_max",
    "currency",
    "salary_text",
    "salary_type",
    "salary_from_text",
]

KNOWN_CITIES = [
    ("ho chi minh", "Ho Chi Minh"),
    ("ha noi", "Ha Noi"),
    ("da nang", "Da Nang"),
    ("can tho", "Can Tho"),
    ("hai phong", "Hai Phong"),
    ("binh duong", "Binh Duong"),
]

VALID_COMPANY_TYPES = {
    "IT Product",
    "IT Outsourcing",
    "IT Service and IT Consulting",
    "Non-IT",
    "Headhunt",
}
