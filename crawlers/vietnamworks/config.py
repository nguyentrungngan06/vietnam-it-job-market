"""
Cấu hình tập trung cho crawler VietnamWorks.
"""
from pathlib import Path
import os

# Thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"

RAW_DIR = DATA_DIR / "raw" / "vietnamworks"
DAILY_DIR = DATA_DIR / "daily"
MASTER_DIR = DATA_DIR / "master"
VIEWS_DIR = DATA_DIR / "views"

MASTER_FILE = MASTER_DIR / "vietnamworks_jobs.csv"

# API Search VietnamWorks
SEARCH_API = "https://ms.vietnamworks.com/job-search/v1.0/search"
ROBOTS_URL = "https://ms.vietnamworks.com/robots.txt"

# IT Category Filter (parentId: 5 = Công Nghệ Thông Tin / Viễn Thông)
IT_FILTER = [{"field": "jobFunction", "value": '[{"parentId": 5, "childrenIds": [-1]}]'}]

RETRIEVE_FIELDS = [
    "address", "benefits", "jobTitle", "salaryMax", "isSalaryVisible", "jobLevelVI", "salaryMin",
    "jobLevel", "jobLevelId", "jobId", "jobUrl", "companyId", "approvedOn", "isAnonymous", "alias",
    "expiredOn", "industries", "industriesV3", "workingLocations", "companyName", "salary",
    "onlineOn", "skills", "jobDescription", "jobRequirement", "prettySalary", "typeWorkingId",
    "createdOn", "numberOfRecruits",
]

# Tỷ giá giả định quy đổi USD -> VND phục vụ phân tích
USD_VND_RATE = 25_000

# User-Agent & Headers
USER_AGENT = os.getenv(
    "CRAWLER_USER_AGENT",
    "Mozilla/5.0 (compatible; VietnamITJobMarketResearchBot/1.0; +https://github.com/nguyentrungngan06/vietnam-it-job-market)"
)

SEARCH_HEADERS = {
    "User-Agent": USER_AGENT,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Language": "vi",
    "Origin": "https://www.vietnamworks.com",
    "Referer": "https://www.vietnamworks.com/",
}

DETAIL_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi,en;q=0.8",
}

HITS_PER_PAGE = 50
DEFAULT_MAX_PAGES = 30
