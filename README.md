# Vietnam IT Job Market

Hệ thống thu thập, theo dõi vòng đời và phân tích dữ liệu thị trường việc làm cùng độ phủ kỹ năng lập trình viên IT tại Việt Nam (VietnamWorks, ITviec, GitHub).

---

## 📁 Cấu trúc dự án

```text
vietnam-it-job-market/
├── crawlers/
│   ├── itviec/              # Module crawl ITviec (Playwright Scraper)
│   │   ├── config.py        # Cấu hình selector, cột chuẩn, 63 tỉnh/thành Việt Nam
│   │   ├── parsers.py       # Bóc tách lương, level, work_mode, company_type, skills (DOM)
│   │   ├── spider.py        # Quét danh sách card (Step 1) & cào chi tiết JD (Step 2)
│   │   ├── pipeline.py      # Khử trùng lặp (dedup), coalesce update Master & lưu snapshot
│   │   └── run.py           # Script thực thi cào ITviec
│   ├── vietnamworks/        # Module crawl & tracking VietnamWorks (REST API)
│   │   ├── config.py        # Cấu hình API, headers, tỷ giá, đường dẫn
│   │   ├── spider.py        # Thu thập Search API & chi tiết tin
│   │   ├── parsers.py       # Bóc tách metadata, quy đổi lương VND
│   │   ├── tracker.py       # Theo dõi vòng đời tin (active/gone, days_alive)
│   │   └── pipeline.py      # Quy trình crawl hoàn chỉnh
│   └── github/              # Module crawl kỹ năng lập trình viên GitHub theo 63 tỉnh/thành
│       ├── config.py        # Cấu hình GitHub API & danh mục địa phương
│       ├── spider.py        # Tìm kiếm users & bóc tách skills qua repos
│       └── pipeline.py      # Tổng hợp & thống kê độ phủ kỹ năng
├── data/                    # Thư mục dữ liệu (tự động tạo khi chạy)
│   ├── daily/               # Snapshot dữ liệu theo từng ngày crawl
│   └── master/              # File tổng hợp toàn bộ lịch sử tin tuyển dụng
├── daily_crawl.py           # Script điều phối chạy crawl hàng ngày qua dòng lệnh
└── README.md
```

---

## 🚀 Cài đặt

Yêu cầu Python 3.10 trở lên. Cài đặt các thư viện cần thiết:

```bash
pip install httpx pandas playwright beautifulsoup4
playwright install chromium
```

---

## ⚡ Hướng dẫn chạy Crawler

### 1. Chạy crawl ITviec hàng ngày
ITviec sử dụng Playwright để quét danh sách việc làm và cào chi tiết JD (tự động checkpoint mỗi 20 bài):
```bash
python crawlers/itviec/run.py
```
*Tùy chọn hữu ích:*
- `--pages 40`: Số trang quét tối đa (mặc định: `40`).
- `--no-headless`: Hiển thị giao diện trình duyệt để quan sát trực quan.
- `--test 5`: Chế độ thử nghiệm, chỉ cào 5 bài đăng chi tiết để kiểm tra.

> **Lưu ý về mức lương:** ITviec yêu cầu đăng nhập để hiển thị mức lương trực tiếp. Đặt file phiên `auth.json` (Playwright cookies) vào thư mục gốc để cào được đầy đủ nhãn lương.

---

### 2. Chạy crawl VietnamWorks hàng ngày
```bash
python daily_crawl.py --site vietnamworks
```
*Tùy chọn hữu ích:* `--pages 30` (số trang), `--enrich-views` (lượt xem/ứng tuyển).

---

### 3. Chạy crawl kỹ năng lập trình viên GitHub
Khuyến khích thiết lập biến môi trường `GITHUB_TOKEN` (tăng hạn mức API lên 5.000 req/giờ):
```bash
# Thiết lập token (PowerShell: $env:GITHUB_TOKEN="...", Linux/macOS: export GITHUB_TOKEN="...")
python daily_crawl.py --site github
```
Hoặc gọi trực tiếp:
```bash
python -m crawlers.github.pipeline
```
*Tùy chọn hữu ích:*
- `--github-token <token>`: Truyền token trực tiếp nếu chưa set env.
- `--users-per-city <N>`: Số hồ sơ tối đa quét mỗi tỉnh (mặc định: `100`).
- `--min-users <N>`: Ngưỡng tối thiểu hồ sơ để xử lý tỉnh (mặc định: `5`).

---

### 4. Chạy toàn bộ các nguồn
```bash
python daily_crawl.py --site all
```

---

## 📊 Luồng xử lý dữ liệu và Kết quả đầu ra

Sau mỗi lần chạy, dữ liệu được chuẩn hóa và lưu tại `data/daily/` và `data/master/`:

- **Tuyển dụng (ITviec):**
  - `data/daily/itviec_clean_YYYY-MM-DD.csv`: Snapshot tin tuyển dụng sạch trong ngày.
  - `data/master/itviec_master.csv`: File tổng hợp toàn bộ lịch sử việc làm ITviec theo cơ chế **Coalesce** (dữ liệu mới làm giàu dữ liệu cũ, không đè rỗng lên trường đã có, gắn cờ `is_duplicate`).
  - `crawl_log.csv`: Ghi nhận lịch sử cào, tổng số tin, số tin có lương và trạng thái (`ok`/`partial`).
- **Tuyển dụng (VietnamWorks):**
  - `data/daily/vietnamworks_YYYY-MM-DD.csv`: Snapshot tin tuyển dụng trong ngày.
  - `data/master/vietnamworks_jobs.csv`: Lịch sử toàn bộ tin tuyển dụng (trạng thái `active`/`gone`, số ngày sống, mức lương VND quy đổi).
- **Kỹ năng nhà phát triển (GitHub):**
  - `data/daily/github_user_profiles_YYYY-MM-DD.csv`: Danh sách lập trình viên theo tỉnh thành kèm các kỹ năng phát hiện được.
  - `data/daily/github_skill_coverage_YYYY-MM-DD.csv`: Tỷ lệ % độ phủ của từng kỹ năng trên tổng số hồ sơ quét được tại từng địa phương.
