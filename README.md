# Vietnam IT Job Market: Crawlers & HR Intelligence Pipeline

Hệ thống mã nguồn mở toàn diện phục vụ thu thập dữ liệu đa nguồn (**VietnamWorks, ITviec, GitHub**), làm sạch, chuẩn hóa kỹ năng 2 tầng, khử trùng lặp có luật bảo vệ chống nối chuỗi (Guard Rule Deduplication) và xây dựng mô hình dữ liệu Star Schema phục vụ phân tích thị trường việc làm công nghệ thông tin tại Việt Nam.

> [!NOTE]
> **Phạm vi dữ liệu của dự án:**
> - **Phân hệ Pipeline & Mart Star-Schema (`data/dashboard/`):** Vận hành trên snapshot Đợt 1 (10/10/2026 – 25/10/2026) gồm 2.019 tin thô $\rightarrow$ **1.884 tin hợp lệ duy nhất** sau khi khử trùng lặp nội bộ bằng Guard Rule.
> - **Phân hệ Phân tích Kỹ năng Chuyên sâu (`01_eda_skill_analysis/`):** Tích hợp toàn diện **2 đợt cào** (từ 10/10 đến giữa tháng 11/2026) với 3.655 lượt quan sát $\rightarrow$ **2.620 tin tuyển dụng độc nhất** sau khi gộp và khử trùng lặp liên đợt bằng khóa thay thế (`site + company + title + city`). Bộ dữ liệu phản ánh lát cắt quan sát thực tế và các phân tích xu hướng mang tính chất mô tả quan sát.

---

## 📁 Cấu Trúc Toàn Diện Kho Lưu Trữ

Dự án tích hợp luồng dữ liệu end-to-end gồm 3 phân hệ chính: Thu thập dữ liệu đa nguồn (`crawlers/`), Làm sạch & Dựng Mart BI (`pipeline/`), và Nghiên cứu chuyên sâu kỹ năng lao động IT (`01_eda_skill_analysis/`):

```text
vietnam-it-job-market/
├── 01_eda_skill_analysis/       # [PHẦN 3] Nghiên cứu chuyên sâu kỹ năng IT Việt Nam (Bước 2 / EDA)
│   ├── README.md                # 📖 Báo cáo tổng hợp toàn diện & diễn giải phương pháp luận
│   ├── reports/                 # 4 báo cáo tiền kỳ, làm sạch & kiểm tra bổ sung (01 - 04)
│   ├── code/                    # Mã nguồn trích xuất ma trận nhị phân 71 kỹ năng chuẩn hóa
│   ├── data/                    # Bảng dữ liệu cơ sở (base/), kiểm toán lọc trùng (dedup_audit/) & taxonomy
│   └── results/                 # Kết quả 4 phần: a_popularity, b_trends, c_cooccurrence, d_network
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
│   ├── test_recruitment_pipeline.py # Bộ kiểm thử tự động 21 Suites kiểm tra toàn vẹn
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

### 2. Chạy Bộ Kiểm Thử Tự Động (21 Test Suites)
Bộ kiểm thử bao gồm kiểm tra chuẩn hóa công ty, bóc tách lương ngoại tệ, bóc tách chuỗi kỹ năng ghép, luật bảo vệ chống nối chuỗi, phân loại vai trò đa tầng và 6 bất biến toàn vẹn dữ liệu:
```bash
python -m unittest pipeline/test_recruitment_pipeline.py
```
*(Kết quả mong đợi: `Ran 21 tests ... OK`)*

### 3. Chạy Pipeline Xử Lý Trên Dữ Liệu Mẫu (Sample Data)
Người dùng có thể chạy thử nghiệm toàn bộ quy trình trên tập dữ liệu mẫu 50 dòng (`data/sample/`):
```bash
python pipeline/run_hr_pipeline.py --input data/sample/itviec_sample.csv data/sample/vietnamworks_sample.csv --out scratch/test_output
```

---

## 📊 Tóm Tắt Kết Quả Xử Lý & Đo Lường Thực Tế

Trên tập dữ liệu quan sát gồm 2.019 tin tuyển dụng (10/10 - 25/10/2026), sau khi khử 135 tin trùng lặp bằng Guard Rule, còn lại **1.884 tin hợp lệ duy nhất** (`valid_job`):
- **Phân bổ nguồn tin hợp lệ:** ITviec đóng góp **927 tin (49.20%)**, VietnamWorks đóng góp **957 tin (50.80%)**.
- **Minh bạch schema:** ITviec có 20 cột rỗng 100% (`job_function`, `level`, `views`, `days_alive`, `industry`...). Do đó, các phân tích về vòng đời tin và lượt xem thuộc độc quyền về VietnamWorks, trong khi dữ liệu kỹ năng, cấp bậc suy luận và mức lương được chuẩn hóa cân bằng trên cả hai sàn.

| Tiêu Chí Đo Lường | Trước Tối Ưu | Sau Chuẩn Hóa | Ý Nghĩa / Giải Pháp |
|---|---|---|---|
| **Kỹ năng chuẩn hóa** | Phân tán nhiều biến thể | **99 nhãn chuẩn** | Xây dựng danh mục Taxonomy 2 tầng (`skill_family`, `skill_category`) |
| **Cấp bậc chưa xác định (`unknown`)** | 57% | **11.69%** (236 tin) | Khai thác suy luận cấp bậc bổ trợ từ số năm kinh nghiệm yêu cầu |
| **Nhóm vị trí chuẩn (`role_group`)** | Không có (chỉ có nhãn thô VNW) | **15 nhóm chuẩn** (Độ chính xác audit 96.0%) | Áp dụng regex phân cấp title chặt + fallback kỹ năng, kiểm định trên 100 mẫu |
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

---

## 🧠 PHẦN 3: PHÂN TÍCH CHUYÊN SÂU KỸ NĂNG IT VIỆT NAM (`01_eda_skill_analysis`)

Phân hệ này chứa toàn bộ quy trình nghiên cứu định lượng, kiểm định phương pháp luận và khai phá dữ liệu (EDA) trên tập mẫu chuẩn hóa **2.620 tin tuyển dụng duy nhất** (kết hợp 2 đợt cào, sau khi khử trùng lặp liên đợt).

Chi tiết báo cáo toàn diện và hướng dẫn phương pháp luận được lưu tại [01_eda_skill_analysis/README.md](01_eda_skill_analysis/README.md).

### 1. Quy Trình Làm Sạch & Gộp Dữ Liệu Liên Đợt (Deduplication Audit)
- **Khóa thay thế (`site + company + title + city`):** Kiểm toán mẫu ngẫu nhiên độc lập 40 cặp tin chỉ khớp bằng khóa thay thế (`surrogate_key_audit_n40.csv`) ghi nhận **40/40 cặp khớp chính xác 100%**, xác nhận độ tin cậy thực nghiệm cao.
- **Khôi phục ngày đăng ITviec:** Nhờ cơ chế liên kết tin trùng với Đợt 2, dự án đã khôi phục thành công ngày đăng thực tế cho **461 tin độc nhất** của ITviec ở Đợt 1, cho phép thiết lập chuỗi quan sát theo tuần trên cả hai nền tảng.
- **Bổ sung chất lượng văn bản:** Toàn bộ tin VietnamWorks Đợt 2 được bổ sung từ snapshot `daily/`, đưa tỷ lệ tin đạt văn bản đầy đủ (`text_quality == 'full'`) lên **99.69%**.

### 2. Tóm Tắt Kết Quả 4 Trọng Tâm Phân Tích Chuyên Sâu

#### A. Phổ Biến Kỹ Năng & Khoảng Tin Cậy Bootstrap Phân Cụm
Thay vì diễn giải thứ hạng đơn lẻ dễ bị nhiễu bởi các doanh nghiệp tuyển dụng hàng loạt, danh mục kỹ năng được chia theo 2 bậc nhu cầu chính:
- **Bậc 1 (Tier 1 - Nhu cầu vượt trội, $\ge 10.5\%$):** 
  1. `English` (16.37%, ITviec: 26.49% vs VNW: 6.49%)
  2. `Python` (15.80%)
  3. `Artificial Intelligence - AI` (14.24%)
  4. `SQL` (14.08%)
  5. `Software Architecture & Design` (10.57%)
  *Top 5 giữ vững tuyệt đối thứ hạng qua cả 3 kịch bản kiểm tra độ nhạy.*
- **Khoảng tin cậy Bootstrap cụm theo công ty (Cluster Bootstrap 95% CI):** Đã tính toán qua 500 vòng lặp tại `ci_wilson_vs_cluster_bootstrap_top15.csv`. Khoảng tin cậy mở rộng từ +1.5% đến +77.0% so với công thức Wilson độc lập, phản ánh đúng độ biến thiên thực tế khi các công ty outsourcing/FDI đăng tin theo chùm.

#### B. Xu Hướng Theo Thời Gian & Kiểm Soát Confounding
- **Ranh giới bước nhảy nguồn (Step-change):** Bảng chéo tuần xác nhận ranh giới phân tách sạch vào ngày 26/10 (các tuần trước 26/10 chiếm $\ge 99\%$ Đợt 1; từ 26/10 trở đi là 100% Đợt 2).
- **Giải mã nghịch lý 70% độ dốc âm:** Kết quả kiểm tra chéo trên sàn ITviec (53.7% âm vs 46.3% dương) và phân tích số kỹ năng trung bình theo tuần chứng minh: Số kỹ năng trung bình đạt đỉnh ở giữa chuỗi (cuối tháng 10) và cơ cấu vai trò tuyển dụng cuối kỳ phân tán hơn. Kết quả **không ủng hộ giả thuyết nhiễu nguồn làm tăng đồng loạt mọi kỹ năng**.
- **Diễn giải cẩn trọng:** Toàn bộ các kiểm định xu hướng đều có $q_{\text{FDR}} \ge 0.09$ (không có ý nghĩa thống kê do chuỗi ngắn 6-9 tuần, có khoảng trống và thiên lệch sống sót). Báo cáo ghi nhận đây là kết quả **chưa đủ bằng chứng kết luận (inconclusive)** và giữ các nhận định ở mức **mô tả quan sát**.

#### C. Cặp Kỹ Năng Đồng Xuất Hiện & FP-Growth
- **Loại trừ chồng chéo định nghĩa (Taxonomy Overlap):** Đo tỷ lệ chứa nhau hai chiều, phát hiện `JavaScript / TypeScript` $\leftrightarrow$ `Angular` đạt mức chứa nhau **97.2%** do cơ chế tick tag của sàn $\implies$ Gắn nhãn chồng chéo định nghĩa để không gây hiểu nhầm cho các thuật toán gợi ý.
- **Phân tách cặp cùng hệ sinh thái vs cặp liên họ:** Phân biệt rõ các cặp cùng hệ sinh thái phân cấp (`Java` $\leftrightarrow$ `Spring`: 87.5% chứa nhau) với các cặp liên họ công nghệ độc lập (`Node.js` $\leftrightarrow$ `React`: NPMI = 0.606; `Python` $\leftrightarrow$ `AI`: Lift = 2.09; `SQL` $\leftrightarrow$ `Python`: Lift = 2.06).
- Xác lập **55 cặp kỹ năng bền vững** qua toàn bộ các lát cắt kiểm định độc lập (`skill_pairs_robust.csv`).

#### D. Mạng Lưới Kỹ Năng & Phân Cụm Louvain
- **Cấu trúc mạng:** Mạng lưới gồm **71 nút kỹ năng** và 75 cạnh liên kết mạnh ($\text{NPMI} \ge 0.3, n_{ij} \ge 10$).
- **10 Cụm công nghệ chính & 16 Kỹ năng độc lập:** Nhận diện 10 cụm công nghệ (Modern Web, DevOps/Cloud, Databases & Backend Languages, IT Infra, Enterprise Java...) cùng danh sách minh bạch 16 kỹ năng cô lập không đạt ngưỡng kết nối (BA, .NET, Cybersecurity, ERP...).
- **Đánh giá Adjusted Rand Index (ARI):** 
  - ARI = 0.8205 (ngưỡng 0.3 vs 0.4 - cấu trúc ổn định theo tham số).
  - ARI = 0.6524 (chia đôi ngẫu nhiên theo công ty - cụm không bị chi phối bởi doanh nghiệp cục bộ).
  - ARI = 0.2736 (giữa ITviec và VNW trên tập nút giao nhau - phản ánh tổng hòa sự khác biệt phân khúc sàn, cơ chế trích xuất và cỡ mẫu chia đôi).

---

## ⚖️ Giấy Phép & Chính Sách Gỡ Dữ Liệu (Takedown Policy)

- **Mã nguồn:** Toàn bộ mã nguồn thu thập và xử lý dữ liệu được phát hành theo giấy phép [MIT License](LICENSE).
- **Dữ liệu công bố:** Dữ liệu trong thư mục `data/dashboard/` và `manual_overrides/` là các chỉ số thống kê, bảng tổng hợp phân tích và metadata đã qua xử lý (chức danh, tên công ty, thành phố, khoảng lương, cấp bậc, nhãn kỹ năng). Dự án **không lưu trữ và không phân phối lại** văn bản mô tả công việc (JD Description) hoặc yêu cầu chi tiết (Job Requirements) của nhà tuyển dụng.
- **Yêu cầu gỡ bỏ thông tin (Data Takedown):** Nếu doanh nghiệp tuyển dụng hoặc các nền tảng có bất kỳ quan ngại nào liên quan đến dữ liệu định danh hoặc mong muốn gỡ bỏ thông tin, xin vui lòng tạo thông báo tại mục **GitHub Issues** của kho lưu trữ. Chúng tôi sẽ tiếp nhận và tiến hành cập nhật bộ từ điển loại trừ trong vòng 48 giờ làm việc.
