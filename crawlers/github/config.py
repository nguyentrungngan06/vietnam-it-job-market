"""
Cấu hình tập trung cho crawler kỹ năng GitHub tại Việt Nam.
"""
from pathlib import Path
import os
import json
import httpx

# Thư mục dự án
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DAILY_DIR = DATA_DIR / "daily"
TOKEN_FILE = ROOT_DIR / ".github_token.json"

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_SAMPLE_USERS_PER_CITY = 100
DEFAULT_MIN_USERS_THRESHOLD = 5

USER_AGENT = "vietnam-it-job-market-crawler/1.0"

BASE_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": USER_AGENT,
}

# 63 tỉnh / thành phố Việt Nam kèm các từ khóa nhận diện địa điểm
LOCATION_QUERIES = {
    # Các Đô thị lớn & Trung tâm công nghệ
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
