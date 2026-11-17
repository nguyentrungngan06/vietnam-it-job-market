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
    # Các trung tâm công nghệ lớn nhất
    ("ho chi minh", "Ho Chi Minh"),
    ("hcm", "Ho Chi Minh"),
    ("sai gon", "Ho Chi Minh"),
    ("ha noi", "Ha Noi"),
    ("hn", "Ha Noi"),
    ("da nang", "Da Nang"),
    ("binh duong", "Binh Duong"),
    ("dong nai", "Dong Nai"),
    ("can tho", "Can Tho"),
    ("hai phong", "Hai Phong"),
    ("ba ria", "Ba Ria - Vung Tau"),
    ("vung tau", "Ba Ria - Vung Tau"),
    ("bac ninh", "Bac Ninh"),
    ("bac giang", "Bac Giang"),
    ("quang ninh", "Quang Ninh"),
    ("vinh phuc", "Vinh Phuc"),
    ("hung yen", "Hung Yen"),
    ("hai duong", "Hai Duong"),
    ("thua thien hue", "Hue"),
    ("hue", "Hue"),
    ("quang nam", "Quang Nam"),
    ("khanh hoa", "Khanh Hoa"),
    ("nha trang", "Khanh Hoa"),
    ("lam dong", "Lam Dong"),
    ("da lat", "Lam Dong"),
    ("long an", "Long An"),
    ("tien giang", "Tien Giang"),
    ("binh dinh", "Binh Dinh"),
    ("quy nhon", "Binh Dinh"),
    ("nghe an", "Nghe An"),
    ("thanh hoa", "Thanh Hoa"),
    ("thai nguyen", "Thai Nguyen"),
    ("phu tho", "Phu Tho"),
    ("nam dinh", "Nam Dinh"),
    ("ha nam", "Ha Nam"),
    ("ninh binh", "Ninh Binh"),
    ("kien giang", "Kien Giang"),
    ("phu quoc", "Kien Giang"),
    ("tay ninh", "Tay Ninh"),
    ("binh phuoc", "Binh Phuc"),
    ("an giang", "An Giang"),
    ("ben tre", "Ben Tre"),
    ("dong thap", "Dong Thap"),
    ("ca mau", "Ca Mau"),
    ("soc trang", "Soc Trang"),
    ("tra vinh", "Tra Vinh"),
    ("hau giang", "Hau Giang"),
    ("vinh long", "Vinh Long"),
    ("bac lieu", "Bac Lieu"),
    ("dak lak", "Dak Lak"),
    ("buon ma thuot", "Dak Lak"),
    ("gia lai", "Gia Lai"),
    ("kon tum", "Kon Tum"),
    ("dak nong", "Dak Nong"),
    ("binh thuan", "Binh Thuan"),
    ("phan thiet", "Binh Thuan"),
    ("ninh thuan", "Ninh Thuan"),
    ("quang tri", "Quang Tri"),
    ("quang binh", "Quang Binh"),
    ("ha tinh", "Ha Tinh"),
    ("thai binh", "Thai Binh"),
    ("hoa binh", "Hoa Binh"),
    ("yen bai", "Yen Bai"),
    ("tuyen quang", "Tuyen Quang"),
    ("lang son", "Lang Son"),
    ("cao bang", "Cao Bang"),
    ("ha giang", "Ha Giang"),
    ("lao cai", "Lao Cai"),
    ("son la", "Son La"),
    ("dien bien", "Dien Bien"),
    ("lai chau", "Lai Chau"),
    ("phu yen", "Phu Yen"),
    ("quang ngai", "Quang Ngai"),
    # Quốc tế / Khác
    ("singapore", "Singapore"),
    ("japan", "Japan"),
    ("tokyo", "Japan"),
    ("remote", "Remote"),
]

VALID_COMPANY_TYPES = {
    "IT Product",
    "IT Outsourcing",
    "IT Service and IT Consulting",
    "Non-IT",
    "Headhunt",
}
