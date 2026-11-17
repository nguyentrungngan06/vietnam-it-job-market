# Vietnam IT Job Market

Hệ thống thu thập, theo dõi vòng đời và phân tích dữ liệu thị trường việc làm cùng độ phủ kỹ năng lập trình viên IT tại Việt Nam (VietnamWorks, ITviec, GitHub).

---

## 📁 Cấu trúc dự án

```text
vietnam-it-job-market/
├── crawlers/
│   ├── vietnamworks/        # Module crawl & tracking VietnamWorks
│   │   ├── config.py        # Cấu hình API, headers, tỷ giá, đường dẫn
│   │   ├── spider.py        # Thu thập Search API & chi tiết tin
│   │   ├── parsers.py       # Bóc tách metadata, quy đổi lương VND
│   │   ├── tracker.py       # Theo dõi vòng đời tin (active/gone, days_alive)
│   │   └── pipeline.py      # Quy trình crawl hoàn chỉnh
│   ├── itviec/              # Module crawl ITviec (Playwright)
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
pip install httpx pandas
```

*(Nếu sử dụng thêm crawler ITviec, cài thêm `playwright` và chạy `playwright install chromium`)*

---

## ⚡ Hướng dẫn chạy Crawler

### 1. Chạy crawl VietnamWorks hàng ngày
```bash
python daily_crawl.py --site vietnamworks
```
*Tùy chọn hữu ích: `--pages 30` (số trang), `--enrich-views` (lượt xem/ứng tuyển).*

### 2. Chạy crawl kỹ năng lập trình viên GitHub
Khuyến khích thiết lập biến môi trường `GITHUB_TOKEN` (tăng hạn mức API lên 5.000 req/giờ):

```bash
# Thiết lập token (Linux/macOS: export GITHUB_TOKEN="...", PowerShell: $env:GITHUB_TOKEN="...")
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

### 3. Chạy toàn bộ các nguồn
```bash
python daily_crawl.py --site all
```

---

## 📊 Dữ liệu đầu ra

Sau mỗi lần chạy, dữ liệu được chuẩn hóa và lưu tại `data/daily/` và `data/master/`:

- **Tuyển dụng (VietnamWorks):**
  - `data/daily/vietnamworks_YYYY-MM-DD.csv`: Snapshot tin tuyển dụng trong ngày.
  - `data/master/vietnamworks_jobs.csv`: Lịch sử toàn bộ tin tuyển dụng (trạng thái `active`/`gone`, số ngày sống, mức lương VND quy đổi).
- **Kỹ năng nhà phát triển (GitHub):**
  - `data/daily/github_user_profiles_YYYY-MM-DD.csv`: Danh sách lập trình viên theo tỉnh thành kèm các kỹ năng phát hiện được.
  - `data/daily/github_skill_coverage_YYYY-MM-DD.csv`: Tỷ lệ % độ phủ của từng kỹ năng trên tổng số hồ sơ quét được tại từng địa phương.
