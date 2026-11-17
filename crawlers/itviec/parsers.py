"""
Module chứa toàn bộ hàm trích xuất (parser) và chuẩn hóa dữ liệu việc làm ITviec.
"""
import hashlib
import re
import unicodedata
from datetime import date, timedelta
from html.parser import HTMLParser
import pandas as pd

from .config import KNOWN_CITIES, VALID_COMPANY_TYPES, SALARY_COLS

SKIP_LINES = {"You'll love it", "Apply now", "HOT", "SUPER HOT", "NEW", "NEW FOR YOU"}
STOP_MARKERS = (
    "job domain", "top 3 reasons", "job description", "mo ta cong viec",
    "linh vuc", "3 ly do", "skills", "ky nang", "your skills",
)
MONEY_RE = re.compile(
    r"(\busd\b|\bvnd\b|vnđ|\$|salary|luong|sign in|dang nhap|you'll love|love it|thoa thuan|negotiable|up to|toi da)",
    re.I,
)


def ascii_lower(s):
    """Chuyển chuỗi về dạng chữ thường không dấu."""
    s = unicodedata.normalize("NFKD", str(s).replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def slugify(s):
    """Tạo slug chuẩn URL từ chuỗi văn bản."""
    s = ascii_lower(s)
    return re.sub(r"[^a-z0-9_]+", "-", s).strip("-")


def slug_ok(slug, url):
    """Kiểm tra slug của công ty có khớp với URL bài đăng."""
    if not slug:
        return False
    job_slug = str(url).split("?")[0].rstrip("/").split("/")[-1]
    m = re.match(r"^(.*)-(\d+)$", job_slug)
    base = m.group(1) if m else job_slug
    return base == slug or base.endswith("-" + slug)


def extract_company(page, text_name, url):
    """Trích xuất tên và slug công ty từ trang chi tiết."""
    try:
        pairs = page.eval_on_selector_all(
            "a[href*='/companies/']",
            "els => els.map(e => [e.getAttribute('href') || '', (e.innerText || '').trim()])",
        )
    except Exception:
        pairs = []

    link_slug, link_name = None, None
    for href, text in pairs:
        m = re.search(r"/companies/([^/?#]+)", href)
        if m and slug_ok(m.group(1), url):
            link_slug = link_slug or m.group(1)
            first = text.split("\n")[0].strip()
            if first and not link_name and len(first) < 100:
                link_name = first

    if text_name and slug_ok(slugify(text_name), url):
        return text_name, link_slug or slugify(text_name)
    if link_name:
        return link_name, link_slug
    if text_name:
        return text_name, link_slug
    return "N/A", link_slug


def make_job_key(url):
    """Tạo khóa định danh duy nhất (job_key) bằng URL đã bỏ query string và dấu gạch chéo cuối."""
    if is_empty_val(url):
        return ""
    return str(url).strip().split("?")[0].rstrip("/")


def generate_numeric_job_id(job_key):
    """Tạo ID số 10 chữ số từ MD5 hash của job_key."""
    if is_empty_val(job_key):
        return ""
    hash_hex = hashlib.md5(str(job_key).encode("utf-8")).hexdigest()[:8]
    numeric_id = int(hash_hex, 16) % 9000000000 + 1000000000
    return str(numeric_id)


def is_empty_val(v):
    """Kiểm tra giá trị rỗng / NaN / N/A."""
    if v is None or pd.isna(v):
        return True
    s = str(v).strip()
    return s in ("", "N/A", "nan", "None", "null", "<NA>")


def is_category_url(url, title):
    """Kiểm tra URL hoặc tiêu đề có phải là trang danh mục / tìm kiếm rác hay không."""
    if is_empty_val(url):
        return True
    if re.search(r"\d+\s+.*jobs?\s+in", str(title), re.I):
        return True
    slug = str(url).split("?")[0].rstrip("/").split("/")[-1]
    # Job URL thực sự của ITviec luôn kết thúc bằng -ID số (ví dụ: ...-12345)
    return not bool(re.search(r"-\d+$", slug))


def parse_salary_fields(sal_vis=None, sal_min=None, sal_max=None, curr=None, sal_text=None):
    """
    Chuẩn hóa và bóc tách thông tin mức lương:
    - Nhận diện dạng dải (range), 'Up to' (tối đa), 'Từ' (tối thiểu).
    - Loại trừ các văn bản trợ cấp / giới thiệu không phải mức lương công việc.
    """
    st = "" if is_empty_val(sal_text) else str(sal_text).strip().replace("\xa0", " ")
    st = re.sub(r"\s+", " ", st)

    has_min = not is_empty_val(sal_min)
    has_max = not is_empty_val(sal_max)

    if has_min or has_max:
        try:
            smin = float(str(sal_min).replace(",", "")) if has_min else None
        except ValueError:
            smin = None
        try:
            smax = float(str(sal_max).replace(",", "")) if has_max else None
        except ValueError:
            smax = None

        if smin is not None or smax is not None:
            c = "USD" if is_empty_val(curr) or str(curr).strip() == "$" else str(curr).strip().upper()
            stype = "range" if (smin is not None and smax is not None) else ("up_to" if smax is not None else "from")
            return {
                "salary_visible": True,
                "salary_min": smin,
                "salary_max": smax,
                "currency": c,
                "salary_text": st if st else None,
                "salary_type": stype,
                "salary_from_text": False,
            }

    if not st:
        return {
            "salary_visible": False,
            "salary_min": None,
            "salary_max": None,
            "currency": None,
            "salary_text": None,
            "salary_type": "missing",
            "salary_from_text": False,
        }

    # Bắt đầu bằng "Up to" / "Upto"
    if re.match(r"^(?:up\s*to)\b", st, re.I):
        has_curr = bool(re.search(r"(\$|usd|vnd|vnđ)", st, re.I))
        m = re.search(r"(?:\$|usd|vnd|vnđ)?\s*([\d,.]+)\s*(?:\$|usd|vnd|vnđ)?", st, re.I)
        if m and has_curr:
            try:
                val = float(m.group(1).replace(",", ""))
                c = "VND" if re.search(r"vnd|vnđ", st, re.I) else "USD"
                return {
                    "salary_visible": False,
                    "salary_min": None,
                    "salary_max": val,
                    "currency": c,
                    "salary_text": st,
                    "salary_type": "up_to",
                    "salary_from_text": True,
                }
            except ValueError:
                pass

    # Bắt đầu bằng "Từ"
    elif re.match(r"^(?:từ|tu)\b", st, re.I):
        has_curr = bool(re.search(r"(\$|usd|vnd|vnđ)", st, re.I))
        m = re.search(r"(?:\$|usd|vnd|vnđ)?\s*([\d,.]+)\s*(?:\$|usd|vnd|vnđ)?", st, re.I)
        if m and has_curr:
            try:
                val = float(m.group(1).replace(",", ""))
                c = "VND" if re.search(r"vnd|vnđ", st, re.I) else "USD"
                return {
                    "salary_visible": False,
                    "salary_min": val,
                    "salary_max": None,
                    "currency": c,
                    "salary_text": st,
                    "salary_type": "from",
                    "salary_from_text": True,
                }
            except ValueError:
                pass

    # Bắt đầu bằng chữ số (dải lương trực tiếp)
    elif re.match(r"^\d", st):
        m_range = re.search(r"^([\d,.]+)\s*[-–~]\s*([\d,.]+)\s*(USD|VND|VNĐ|\$)?", st, re.I)
        if m_range:
            try:
                smin = float(m_range.group(1).replace(",", ""))
                smax = float(m_range.group(2).replace(",", ""))
                curr_str = m_range.group(3) or ""
                c = "VND" if curr_str.upper() in ("VND", "VNĐ") else "USD"
                return {
                    "salary_visible": True,
                    "salary_min": smin,
                    "salary_max": smax,
                    "currency": c,
                    "salary_text": st,
                    "salary_type": "range",
                    "salary_from_text": True,
                }
            except ValueError:
                pass

    return {
        "salary_visible": False,
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "salary_text": None,
        "salary_type": "missing",
        "salary_from_text": False,
    }


def clean_company_size(val):
    """
    Chuẩn hóa quy mô công ty:
    - Loại trừ các năm giải thưởng bị bắt nhầm ('2022\\nNhân viên').
    - Giữ lại số đầu hoặc khoảng nhân viên hợp lệ (1-50, 151-300, 1000+).
    """
    if is_empty_val(val):
        return "unknown"
    s = str(val).strip()
    if s.lower() == "unknown":
        return "unknown"
    if "\n" in s and re.match(r"^20(1\d|2\d)\s*\n", s):
        return "unknown"

    s_flat = re.sub(r"\s+", " ", s).strip()
    m_range = re.match(r"^(\d+)\s*[-–]\s*(\d+)\s*(?:employees|nhân viên)?$", s_flat, re.I)
    if m_range:
        first_num = int(m_range.group(1))
        if 1 <= first_num <= 100000:
            return str(first_num)

    m_plus = re.match(r"^(\d+)\+?\s*(?:employees|nhân viên)?$", s_flat, re.I)
    if m_plus:
        first_num = int(m_plus.group(1))
        if 2018 <= first_num <= 2026 or first_num < 5:
            return "unknown"
        if 5 <= first_num <= 100000:
            return str(first_num)

    return "unknown"


def infer_level(title, requirement="", description=""):
    """Suy luận cấp bậc (level) từ tiêu đề và JD."""
    t = "" if is_empty_val(title) else str(title)
    req = "" if is_empty_val(requirement) else str(requirement)
    desc = "" if is_empty_val(description) else str(description)

    # 1. Ưu tiên xét trên tiêu đề công việc
    if re.search(r"\b(intern|internship|thực tập|thuc tap|trainee)\b", t, re.I):
        return "Intern"
    if re.search(r"\b(fresher|graduate|mới tốt nghiệp)\b", t, re.I):
        return "Fresher"
    if re.search(r"\b(director|head\b|vp\b|chief|cto\b|cio\b|cpo\b|giám đốc|giam doc)\b", t, re.I):
        return "Director"
    if re.search(r"\b(manager|quản lý|quan ly|trưởng phòng|truong phong|project manager|product manager)\b", t, re.I):
        return "Manager"
    if re.search(r"\b(lead|leader|team lead|tech lead|principal|architect|trưởng nhóm|truong nhom)\b", t, re.I):
        return "Lead"
    if re.search(r"\b(senior|sr\.?\b|chuyên gia|cao cấp|expert)\b", t, re.I):
        return "Senior"
    if re.search(r"\b(junior|jr\.?\b)\b", t, re.I):
        return "Junior"
    if re.search(r"\b(middle|mid-level|mid\b|chuyên viên)\b", t, re.I):
        return "Middle"

    # 2. Xét trong yêu cầu kinh nghiệm của JD
    full_jd = f"{req}\n{desc}"
    if re.search(r"\b(sinh viên năm cuối|thực tập sinh|internship)\b", full_jd, re.I):
        return "Intern"

    exp_matches = re.findall(
        r"(?:at least|minimum|tối thiểu|từ|over|trên|about|khoảng)?\s*(\d{1,2})\s*(?:\+|\-\s*\d{1,2})?\s*(?:years?|năm|yrs?)\s*(?:of\s+)?(?:experience|kinh nghiệm|working|làm việc)",
        full_jd,
        re.I,
    )
    if exp_matches:
        years = [int(y) for y in exp_matches if int(y) <= 25]
        if years:
            min_y = min(years)
            if min_y == 0:
                return "Fresher"
            if min_y <= 1:
                return "Junior"
            if min_y <= 3:
                return "Middle"
            return "Senior"

    return "Middle"


def infer_work_mode(title, description="", requirement="", raw_work_mode=None):
    """Suy luận hình thức làm việc (At office / Hybrid / Remote)."""
    if not is_empty_val(raw_work_mode):
        rw = str(raw_work_mode).strip()
        if rw in ("At office", "Hybrid", "Remote"):
            return rw
        if "tại văn phòng" in rw.lower():
            return "At office"
        if "linh hoạt" in rw.lower():
            return "Hybrid"
        if "từ xa" in rw.lower():
            return "Remote"

    t = "" if is_empty_val(title) else str(title)
    jd = f"{t}\n{'' if is_empty_val(description) else description}\n{'' if is_empty_val(requirement) else requirement}"

    if re.search(r"\b(remote|work from home|wfh|làm việc từ xa|100%\s*remote)\b", t, re.I):
        return "Remote"
    if re.search(r"\b(hybrid|linh hoạt)\b", t, re.I):
        return "Hybrid"
    if re.search(r"\b(hybrid|working model:\s*hybrid|làm việc linh hoạt|\d+\s*days?\s*(?:wfh|remote|work from home))\b", jd, re.I):
        return "Hybrid"
    if re.search(r"\b(100%\s*remote|full\s*remote|fully\s*remote|làm việc từ xa hoàn toàn)\b", jd, re.I):
        return "Remote"
    return "At office"


def infer_company_type(company, description="", requirement="", raw_company_type=None):
    """Suy luận loại hình công ty (IT Product / IT Outsourcing / IT Service / Non-IT)."""
    if not is_empty_val(raw_company_type):
        rc = str(raw_company_type).strip()
        if rc in VALID_COMPANY_TYPES:
            return rc

    comp = "" if is_empty_val(company) else str(company)
    jd = f"{comp}\n{'' if is_empty_val(description) else description}\n{'' if is_empty_val(requirement) else requirement}"

    if re.search(
        r"\b(bank|ngân hàng|vpbank|techcombank|mbbank|mb bank|vietinbank|vietcombank|acb|ocb|vib|shb|lpbank|seabank|msb|hdbank|tpbank|securities|chứng khoán|insurance|bảo hiểm|bệnh viện|hospital|university|đại học|airlines|hàng không|retail|bán lẻ|sun group|vingroup|masan|fpt retail|con cưng|con cung|pharmacity)\b",
        comp,
        re.I,
    ):
        return "Non-IT"

    if re.search(r"\b(outsourcing|outsource|offshore|odc\b|global clients|khách hàng nhật|thị trường nhật)\b", jd, re.I):
        return "IT Outsourcing"

    if re.search(r"\b(consulting|tư vấn|system integration|tích hợp hệ thống|it services|dịch vụ cntt|managed services)\b", jd, re.I):
        return "IT Service and IT Consulting"

    if re.search(r"\b(product|sản phẩm|saas|platform|fintech|e-commerce|game|studio|ai\b)\b", jd, re.I):
        return "IT Product"

    return "unknown"


def infer_posted_date(ref_date=None, raw_posted_text=None):
    """
    Tính ngày đăng bài từ chuỗi tương đối (vd: 'Posted 3 days ago' -> YYYY-MM-DD).
    Đảm bảo quy tắc: posted_date <= ngày tham chiếu (ref_date).
    """
    ref_date = ref_date or date.today().isoformat()
    if is_empty_val(raw_posted_text):
        return ref_date

    s = str(raw_posted_text).strip()
    m_days = re.search(r"(\d+)\s*(?:days?|ngày)", s, re.I)
    if m_days:
        days = int(m_days.group(1))
        base = date.fromisoformat(ref_date)
        return (base - timedelta(days=days)).isoformat()
    if re.search(r"(?:hours?|minutes?|giờ|phút)", s, re.I):
        return ref_date

    return ref_date


class _FlatHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg"):
            self._skip += 1
        elif tag == "a":
            self.events.append(("a_start", dict(attrs).get("href") or ""))
        elif tag in ("h2", "h3", "h4"):
            self.events.append(("block", tag))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg"):
            self._skip = max(0, self._skip - 1)
        elif tag == "a":
            self.events.append(("a_end", None))
        elif tag == "h1":
            self.events.append(("h1_end", None))

    def handle_data(self, data):
        if self._skip:
            return
        data = re.sub(r"\s+", " ", data).strip()
        if data:
            self.events.append(("text", data))


def parse_job_skills(html):
    """
    Trích xuất chính xác danh sách Skills của job từ DOM HTML.
    Tránh quét nhầm toàn bộ menu Navigation và các job gợi ý ở cuối trang.
    """
    if not html:
        return "N/A"
    p = _FlatHTMLParser()
    p.feed(html)
    ev = p.events

    # Bỏ qua mọi phần tử trước thẻ đóng </h1> (menu điều hướng)
    start = next((i for i, e in enumerate(ev) if e[0] == "h1_end"), None)
    if start is None:
        return "N/A"

    # Tìm nhãn "Skills:" đầu tiên sau tiêu đề
    label_idx, in_a = None, False
    for i in range(start + 1, len(ev)):
        k = ev[i][0]
        if k == "a_start":
            in_a = True
        elif k == "a_end":
            in_a = False
        elif k == "text" and not in_a and ascii_lower(ev[i][1]).rstrip(":") in ("skills", "skill", "ky nang"):
            label_idx = i
            break

    if label_idx is None:
        return "N/A"

    skills = []
    cur_href, cur_text = None, []
    for k, v in ev[label_idx + 1:]:
        if k == "a_start":
            cur_href, cur_text = v, []
        elif k == "a_end":
            if cur_href and "/it-jobs/" in cur_href:
                val = " ".join(cur_text).strip()
                if val and val.lower() not in ("show all", "see all", "view all", "xem tat ca"):
                    if val not in skills:
                        skills.append(val)
            cur_href, cur_text = None, []
        elif k == "text" and cur_href is not None:
            cur_text.append(v)
        elif k in ("block", "h1_end") or (k == "text" and ascii_lower(v).rstrip(":") in ("job expertise", "job domain", "top 3 reasons", "job description")):
            break

    return " | ".join(skills) if skills else "N/A"


def header_lines(body_text, title):
    """Lấy các dòng sau tiêu đề để tìm thông tin công ty và địa chỉ."""
    if is_empty_val(title) or title not in body_text:
        return []
    return [l.strip() for l in body_text.split(title, 1)[1].split("\n") if l.strip()]


def looks_like_address(line):
    if "," not in line or len(line) > 250 or MONEY_RE.search(ascii_lower(line)):
        return False
    last = line.split(",")[-1].strip()
    return 0 < len(last) < 40 and not re.search(r"\d", last)


def find_address(lines):
    first_ok = None
    for line in lines[:10]:
        low = ascii_lower(line)
        if low.startswith(STOP_MARKERS):
            break
        if low in [name.lower() for _, name in KNOWN_CITIES]:
            return line
        if not looks_like_address(line):
            continue
        if any(k in ascii_lower(line.split(",")[-1]) for k, _ in KNOWN_CITIES):
            return line
        first_ok = first_ok or line
    return first_ok


def split_company_address(lines):
    i = 0
    while i < len(lines) and lines[i] in SKIP_LINES:
        i += 1
    if i >= len(lines) or len(lines[i]) >= 100:
        return None, None
    return lines[i], find_address(lines[i + 1:])


def city_from_address(addr):
    if is_empty_val(addr):
        return "N/A"
    last = addr.split(",")[-1].strip()
    for key, name in KNOWN_CITIES:
        if key in ascii_lower(last):
            return name
    for key, name in KNOWN_CITIES:
        if key in ascii_lower(addr):
            return name
    return last if ("," in addr and 0 < len(last) < 40) else "N/A"


def extract_page_metadata(body_text, title):
    """Trích xuất metadata hiển thị trực tiếp trong khối tổng quan trang chi tiết."""
    after = body_text.split(title, 1)[1] if (title and title != "N/A" and title in body_text) else body_text
    main_part = after.split("More jobs for you")[0].split("Việc làm tương tự")[0]
    header_part = main_part.split("Job description")[0].split("Mô tả công việc")[0]

    wm = re.search(r"\n\s*(At office|Hybrid|Remote|Tại văn phòng|Linh hoạt|Từ xa)\s*\n", header_part, re.I)
    post = re.search(r"(Posted\s+[^\n]+?ago|Đăng\s+[^\n]+?trước)", header_part, re.I)
    ctype = re.search(r"(?:Company type|Mô hình công ty)\s*\n+\s*([^\n]+)", main_part, re.I)
    csize = re.search(r"(?:Company size|Quy mô công ty)\s*\n+\s*([^\n]+(?:\n\s*(?:employees|nhân viên))?)", main_part, re.I)

    return {
        "raw_work_mode": wm.group(1).strip() if wm else None,
        "raw_posted_text": post.group(1).strip() if post else None,
        "raw_company_type": ctype.group(1).strip() if ctype else None,
        "raw_company_size": re.sub(r"\s+", " ", csize.group(1)).strip() if csize else None,
    }
