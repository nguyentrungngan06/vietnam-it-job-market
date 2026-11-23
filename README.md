# Vietnam IT Job Market: Crawlers & HR Intelligence Pipeline

Hệ thống mã nguồn mở toàn diện phục vụ thu thập dữ liệu đa nguồn (**VietnamWorks, ITviec, GitHub**), làm sạch, chuẩn hóa kỹ năng 2 tầng, khử trùng lặp có luật bảo vệ chống nối chuỗi (Guard Rule Deduplication) và xây dựng mô hình dữ liệu Star Schema phục vụ phân tích thị trường việc làm công nghệ thông tin tại Việt Nam.

> [!NOTE]
> **Phạm vi dữ liệu:** Bộ dữ liệu quan sát được thu thập từ 2 nền tảng tuyển dụng (**ITviec** và **VietnamWorks**) trong khoảng thời gian từ **10/10/2026 đến 25/10/2026** (khoảng 2.000 tin tuyển dụng). Tập dữ liệu phản ánh lát cắt quan sát trong chu kỳ 15 ngày trên 2 nền tảng nêu trên và không mang tính đại diện tuyệt đối cho toàn bộ thị trường lao động IT tại Việt Nam.

---

## 📁 Cấu Trúc Toàn Diện Kho Lưu Trữ

Dự án tích hợp luồng dữ liệu end-to-end từ tầng thu thập (`crawlers/`), tầng làm sạch & phân tích (`pipeline/`) đến tầng lưu trữ dữ liệu BI (`data/dashboard/`):

```text
vietnam-it-job-market/
├── crawlers/                    # [PHẦN 1] Module thu thập dữ liệu đa nguồn
│   ├── itviec/                  # Playwright Scraper cào danh sách card & chi tiết JD ITviec
│   │   ├── config.py            # Cấu hình selector, cột chuẩn, 63 tỉnh/thành
│   │   ├── parsers.py           # Bóc tách lương, level, work_mode, company_type, skills
│   │   ├── spider.py            # Quét danh sách & cào JD chi tiết (checkpoint mỗi 20 bài)
│   │   ├── pipeline.py          # Khử trùng lặp, cập nhật Master & lưu snapshot
│   │   └── run.py               # Script thực thi cào ITviec
│   ├── vietnamworks/            # REST API client & theo dõi vòng đời tin VietnamWorks
│   │   ├── config.py            # Cấu hình Search API, headers, User-Agent, tỷ giá
│   │   ├── spider.py            # Thu thập Search API & bóc tách chi tiết tin
│   │   ├── parsers.py           # Bóc tách metadata, quy đổi lương VND
│   │   ├── tracker.py           # Theo dõi vòng đời tin (active/gone, days_alive)
│   │   ├── pipeline.py          # Quy trình crawl hoàn chỉnh
│   │   └── run.py               # Script thực thi cào VietnamWorks
│   ├── github/                  # Client quét kỹ năng lập trình viên theo 63 tỉnh/thành
│   │   ├── config.py            # Cấu hình GitHub Search API & danh mục địa phương
│   │   ├── spider.py            # Tìm kiếm developer & bóc tách kỹ năng qua repos
│   │   └── pipeline.py          # Tổng hợp độ phủ kỹ năng địa phương
│   └── README.md                # 📖 Hướng dẫn chi tiết phân hệ Crawlers
├── pipeline/                    # [PHẦN 2] Data Pipeline xử lý, chuẩn hóa & xây dựng Mart
│   ├── recruitment_pipeline.py  # Làm sạch, map kỹ năng 2 tầng, khử trùng lặp (Guard Rule)
│   ├── dashboard_data.py        # Dựng Star Schema (Fact/Dim) & tính chỉ số kỹ năng 0-100
│   ├── jd_analysis.py           # Bóc tách số năm kinh nghiệm, cấp bậc, tầm quan trọng kỹ năng
│   ├── run_hr_pipeline.py       # Script điều phối thực thi pipeline từ dòng lệnh
│   ├── test_recruitment_pipeline.py # Bộ kiểm thử tự động 20 Suites kiểm tra toàn vẹn
│   ├── quality_report.json      # Báo cáo chất lượng dữ liệu & các giả định quy đổi
│   ├── requirements.txt         # Khai báo thư viện phụ thuộc cho pipeline
│   └── README.md                # 📖 Hướng dẫn kỹ thuật chi tiết phân hệ Pipeline
├── manual_overrides/            # Từ điển chuẩn & các file đối soát chất lượng dữ liệu
│   ├── skill_taxonomy.csv       # Danh mục 99 kỹ năng chuẩn (skill_family, skill_category)
│   ├── skill_alias.csv          # 1.696 quy tắc ánh xạ alias kỹ năng và xử lý chuỗi ghép
│   ├── duplicate_audit_sample_20_filled.csv  # Mẫu đối soát 20 cặp tin gộp tự động
│   ├── duplicate_validation_sample_30.csv    # Kiểm định độc lập 30 cặp tin mới (100% khớp)
│   ├── duplicate_review_filled.csv           # Đối soát thủ công 7 cặp tin trùng nghi vấn
│   ├── salary_review_filled.csv              # 29 bản ghi hiệu chỉnh lương bất thường
│   ├── skill_review_filled.csv               # Bảng tra cứu nhãn kỹ năng đã xác thực
│   └── VERSION.md               # Nhật ký phiên bản danh mục override
├── data/
│   ├── dashboard/               # Tầng dữ liệu Star-Schema phục vụ Dashboard BI & Analytics
│   │   ├── fact_jobs.csv        # Bảng Fact tin tuyển dụng (chỉ chứa metadata chuẩn hóa)
│   │   ├── fact_job_skills.csv  # Bảng Fact kỹ năng theo từng tin tuyển dụng
│   │   ├── dim_companies.csv    # Bảng Dim phân khúc doanh nghiệp và quy mô tuyển dụng
│   │   ├── skill_demand_index.csv # Chỉ số nhu cầu kỹ năng (thang 0-100 kèm phân tích độ nhạy)
│   │   ├── salary_benchmarks.csv  # Chuẩn mực lương theo vai trò x cấp bậc (ẩn khi n < 5)
│   │   └── dashboard_quality.json # Báo cáo kiểm định chất lượng bảng dashboard
│   └── sample/                  # Dữ liệu mẫu (50 dòng) để người dùng chạy thử pipeline
│       ├── itviec_sample.csv
│       └── vietnamworks_sample.csv
├── daily_crawl.py               # Script điều phối chạy crawl hàng ngày qua dòng lệnh
├── crawl_github.py              # Script cào GitHub developer theo địa phương
├── save_session.py              # Tiện ích lưu Playwright cookies (auth.json)
├── CHANGELOG.md                 # Nhật ký thay đổi và các chỉ số đo lường thực tế
├── LICENSE                      # Giấy phép mã nguồn mở (MIT)
└── README.md                    # Tài liệu tổng quan dự án
```

---

## ⚡ PHẦN 1: HƯỚNG DẪN VẬN HÀNH BỘ THU THẬP DỮ LIỆU (CRAWLERS)

Yêu cầu môi trường Python 3.10 trở lên. Cài đặt các thư viện cần thiết:

```bash
pip install httpx pandas playwright beautifulsoup4
playwright install chromium
```

Chi tiết tài liệu từng module được lưu tại [crawlers/README.md](crawlers/README.md).

### 1. Chạy Crawl ITviec Hàng Ngày
ITviec sử dụng Playwright (Chromium Headless) để quét danh sách việc làm và cào chi tiết JD (tự động checkpoint mỗi 20 bài):

```bash
python crawlers/itviec/run.py
```

*Các tùy chọn dòng lệnh:*
- `--pages 40`: Số trang danh sách tối đa cần quét (mặc định: `40`).
- `--no-headless`: Mở giao diện trình duyệt trực quan để quan sát quá trình chạy.
- `--test 5`: Chế độ chạy thử, chỉ cào 5 bài đăng chi tiết để kiểm thử bộ bóc tách.

> **Lưu ý về nhãn lương ITviec:** ITviec yêu cầu phiên đăng nhập để hiển thị dải lương trực tiếp. Đặt file phiên `auth.json` (Playwright cookies được tạo từ `save_session.py`) vào thư mục gốc để thu thập được đầy đủ mức lương.

---

### 2. Chạy Crawl VietnamWorks Hàng Ngày
Có thể thực thi trực tiếp module VietnamWorks hoặc gọi qua script điều phối:

```bash
# Cách 1: Gọi trực tiếp module VietnamWorks
python crawlers/vietnamworks/run.py

# Cách 2: Gọi qua script điều phối chung
python daily_crawl.py --site vietnamworks
```

#### Hai chế độ crawl:
- **Chế độ Crawl Nhanh (Mặc định - thời gian ~1 phút):**
  Quét toàn bộ Search API (nhóm ngành Công nghệ thông tin / Viễn thông), chuẩn hóa bảng dữ liệu, quy đổi lương VND, lưu snapshot Daily và cập nhật trạng thái vòng đời tin vào Master:
  ```bash
  python crawlers/vietnamworks/run.py
  ```
- **Chế độ Crawl Đầy đủ (`--enrich-views` - thời gian ~25–30 phút):**
  Thực hiện bước Crawl Nhanh kết hợp duyệt chi tiết từng URL tuyển dụng để bóc tách lượt xem (`views`), số hồ sơ ứng tuyển (`applications`), mô tả công việc và lưu lịch sử vào `data/views/views_YYYY-MM-DD.csv`:
  ```bash
  python crawlers/vietnamworks/run.py --enrich-views
  ```

*Các tùy chọn dòng lệnh:*
- `--pages <N>`: Giới hạn số trang cào (mặc định: `30`, khoảng 1.500 tin).
- `--enrich-views`: Bật chế độ cào sâu lượt xem, ứng tuyển và nội dung chi tiết.
- `--date YYYY-MM-DD`: Chỉ định ngày crawl cụ thể (mặc định: hôm nay).
- `--save-raw`: Lưu bản sao JSON thô từng trang vào `data/raw/vietnamworks/`.
- `--partial`: Chế độ crawl dở dang (không đánh dấu `gone` cho các tin cũ chưa quét tới).

---

### 3. Chạy Crawl Kỹ Năng Lập Trình Viên GitHub
Khuyến khích thiết lập biến môi trường `GITHUB_TOKEN` để tăng hạn mức API từ 60 lên 5.000 requests/giờ:

```bash
# Thiết lập token (PowerShell: $env:GITHUB_TOKEN="...", Linux/macOS: export GITHUB_TOKEN="...")
python daily_crawl.py --site github

# Hoặc gọi trực tiếp module GitHub
python -m crawlers.github.pipeline
```

*Các tùy chọn hữu ích:*
- `--github-token <token>`: Truyền token trực tiếp qua tham số dòng lệnh.
- `--users-per-city <N>`: Số hồ sơ nhà phát triển tối đa quét cho mỗi tỉnh/thành (mặc định: `100`).
- `--min-users <N>`: Ngưỡng tối thiểu hồ sơ để xử lý thống kê cho địa phương (mặc định: `5`).

---

### 4. Điều Phối Chạy Toàn Bộ Các Nguồn
```bash
python daily_crawl.py --site all
```

---

### 5. Luồng Dữ Liệu Tầng Crawler & Cơ Chế Coalesce
Sau khi thu thập, dữ liệu được ghi nhận vào `data/daily/` và `data/master/`:
- **ITviec Master (`data/master/itviec_master.csv`):** Áp dụng cơ chế **Coalesce** — dữ liệu mới làm giàu dữ liệu cũ, không đè giá trị rỗng lên các trường đã thu thập trước đó, gắn cờ `is_duplicate`.
- **VietnamWorks Master (`data/master/vietnamworks_jobs.csv`):** Theo dõi trạng thái vòng đời tin (`active` / `gone`), số ngày tồn tại (`days_alive`) và quy đổi lương tương đương VND.
- **GitHub Coverage (`data/daily/github_skill_coverage_YYYY-MM-DD.csv`):** Tỷ lệ % độ phủ của từng công nghệ trên tổng số hồ sơ quét được tại từng địa phương trong 63 tỉnh/thành.

---

## 🔬 PHẦN 2: HƯỚNG DẪN DATA PIPELINE & MÔ HÌNH STAR-SCHEMA

Chi tiết tài liệu kỹ thuật phân hệ xử lý được lưu tại [pipeline/README.md](pipeline/README.md).

### 1. Cài Đặt Thư Viện Pipeline
```bash
pip install -r pipeline/requirements.txt
```

### 2. Chạy Bộ Kiểm Thử Tự Động (20 Test Suites)
Bộ kiểm thử bao gồm kiểm tra chuẩn hóa công ty, bóc tách lương ngoại tệ, bóc tách chuỗi kỹ năng ghép, luật bảo vệ chống nối chuỗi và 6 bất biến toàn vẹn dữ liệu:
```bash
python -m unittest pipeline/test_recruitment_pipeline.py
```
*(Kết quả mong đợi: `Ran 20 tests ... OK`)*

### 3. Chạy Pipeline Xử Lý Trên Dữ Liệu Mẫu (Sample Data)
Người dùng có thể chạy thử nghiệm toàn bộ quy trình trên tập dữ liệu mẫu 50 dòng (`data/sample/`):
```bash
python pipeline/run_hr_pipeline.py --input data/sample/itviec_sample.csv data/sample/vietnamworks_sample.csv --out scratch/test_output
```

---

## 📊 Tóm Tắt Kết Quả Xử Lý & Đo Lường Thực Tế

Trên tập dữ liệu quan sát gồm 2.019 tin tuyển dụng (10/10 - 25/10/2026):

| Tiêu Chí Đo Lường | Trước Tối Ưu | Sau Chuẩn Hóa | Ý Nghĩa / Giải Pháp |
|---|---|---|---|
| **Kỹ năng chuẩn hóa** | Phân tán nhiều biến thể | **99 nhãn chuẩn** | Xây dựng danh mục Taxonomy 2 tầng (`skill_family`, `skill_category`) |
| **Cấp bậc chưa xác định (`unknown`)** | 57% | **11.69%** (236 tin) | Khai thác suy luận cấp bậc bổ trợ từ số năm kinh nghiệm yêu cầu |
| **Vai trò chưa phân loại (`other`)** | 40% | **26.80%** (541 tin) | Mở rộng hệ luật regex nhận diện 20 vai trò công nghệ chuyên biệt |
| **Ô chuẩn mực lương tin cậy ($n \ge 5$)** | Nhiều ô $n < 5$ bị méo mó | **27 / 96 ô** | Triệt tiêu hiển thị (gán `NaN`) cho các ô $n < 5$ để tránh sai lệch thống kê |
| **Chất lượng văn bản mô tả (`full`)** | Không phân loại | **1.583 / 2.019 tin (78.4%)** | Đánh giá độ dài mô tả và làm giàu tin VietnamWorks |
| **Độ chính xác khử trùng lặp (Guard Rule)** | Dễ nối chuỗi sai | **30/30 (100%)** | Kiểm định độc lập 30 cặp tin mới (`duplicate_validation_sample_30.csv`) |

---

## 📈 Chỉ Số Nhu Cầu Kỹ Năng (`skill_demand_index`)

Chỉ số nhu cầu kỹ năng (thang 0–100) được tính theo trọng số chuẩn hóa bách phân vị:

$$\text{Index} = 100 \times \left( 0.45 \times P_{\text{job}} + 0.35 \times P_{\text{company}} + 0.20 \times S_{\text{required}} \right)$$

- $P_{\text{job}}$: Thứ hạng bách phân vị theo quy mô tin tuyển dụng (45%).
- $P_{\text{company}}$: Thứ hạng bách phân vị theo độ phân tán doanh nghiệp (35%). Tránh việc 1 đơn vị đăng hàng loạt làm sai lệch chỉ số.
- $S_{\text{required}}$: Tỷ lệ yêu cầu bắt buộc của kỹ năng trong tin đăng (20%).

*Phân tích độ nhạy (Sensitivity Analysis):* Kiểm định với các kịch bản trọng số thay thế (Cân bằng, Thiên lượng tin) đạt hệ số tương quan Spearman $r_s > 0.98$, khẳng định thứ hạng top kỹ năng ổn định trước các giả định trọng số.

---

## ⚖️ Giấy Phép & Chính Sách Gỡ Dữ Liệu (Takedown Policy)

- **Mã nguồn:** Toàn bộ mã nguồn thu thập và xử lý dữ liệu được phát hành theo giấy phép [MIT License](LICENSE).
- **Dữ liệu công bố:** Dữ liệu trong thư mục `data/dashboard/` và `manual_overrides/` là các chỉ số thống kê, bảng tổng hợp phân tích và metadata đã qua xử lý (chức danh, tên công ty, thành phố, khoảng lương, cấp bậc, nhãn kỹ năng). Dự án **không lưu trữ và không phân phối lại** văn bản mô tả công việc (JD Description) hoặc yêu cầu chi tiết (Job Requirements) của nhà tuyển dụng.
- **Yêu cầu gỡ bỏ thông tin (Data Takedown):** Nếu doanh nghiệp tuyển dụng hoặc các nền tảng có bất kỳ quan ngại nào liên quan đến dữ liệu định danh hoặc mong muốn gỡ bỏ thông tin, xin vui lòng tạo thông báo tại mục **GitHub Issues** của kho lưu trữ. Chúng tôi sẽ tiếp nhận và tiến hành cập nhật bộ từ điển loại trừ trong vòng 48 giờ làm việc.
