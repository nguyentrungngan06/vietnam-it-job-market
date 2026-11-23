# Vietnam IT Job Market: Crawlers & HR Intelligence Pipeline

Hệ thống mã nguồn mở toàn diện phục vụ thu thập dữ liệu đa nguồn (ITviec, VietnamWorks, GitHub), làm sạch, chuẩn hóa kỹ năng 2 tầng, khử trùng lặp có luật bảo vệ chống nối chuỗi (Guard Rule Deduplication) và xây dựng mô hình dữ liệu Star Schema phục vụ phân tích thị trường việc làm công nghệ thông tin tại Việt Nam.

> [!NOTE]
> **Phạm vi dữ liệu:** Bộ dữ liệu quan sát được thu thập từ 2 nền tảng tuyển dụng (**ITviec** và **VietnamWorks**) trong khoảng thời gian từ **10/10/2026 đến 25/10/2026** (khoảng 2.000 tin tuyển dụng). Tập dữ liệu phản ánh lát cắt quan sát trong chu kỳ 15 ngày trên 2 nền tảng nêu trên và không mang tính đại diện tuyệt đối cho toàn bộ thị trường lao động IT tại Việt Nam.

---

## 📁 Cấu Trúc Kho Lưu Trữ

Dự án được phân chia thành 2 phân hệ độc lập kèm dữ liệu mart phục vụ khai thác trực tiếp:

```text
vietnam-it-job-market/
├── crawlers/                    # [PHẦN 1] Module thu thập dữ liệu đa nguồn
│   ├── itviec/                  # Playwright scraper bóc tách tin tuyển dụng ITviec
│   ├── vietnamworks/            # REST API client & vòng đời tin tuyển dụng VietnamWorks
│   ├── github/                  # API client quét kỹ năng lập trình viên theo 63 tỉnh thành
│   └── README.md                # 📖 Hướng dẫn chi tiết phân hệ Crawlers
├── pipeline/                    # [PHẦN 2] Data Pipeline xử lý, chuẩn hóa & xây dựng Mart
│   ├── recruitment_pipeline.py  # Làm sạch, map kỹ năng 2 tầng, khử trùng lặp (Guard Rule)
│   ├── dashboard_data.py        # Mô hình Star Schema (Fact/Dim) & tính chỉ số kỹ năng
│   ├── run_hr_pipeline.py       # Script điều phối thực thi pipeline từ dòng lệnh
│   ├── test_recruitment_pipeline.py # Bộ kiểm thử tự động 20 Suites
│   ├── quality_report.json      # Báo cáo đo lường chất lượng & các giả định quy đổi
│   ├── requirements.txt         # Thư viện phụ thuộc cho pipeline
│   └── README.md                # 📖 Hướng dẫn kỹ thuật chi tiết phân hệ Pipeline
├── manual_overrides/            # Từ điển chuẩn & các mẫu đối soát chất lượng dữ liệu
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
├── CHANGELOG.md                 # Nhật ký thay đổi và các chỉ số đo lường thực tế
├── LICENSE                      # Giấy phép mã nguồn mở (MIT)
└── README.md                    # Tài liệu tổng quan dự án
```

---

## 🚀 Hướng Dẫn Nhanh (Quickstart)

### 1. Phân Hệ Thu Thập Dữ Liệu (Crawlers)
Xem hướng dẫn chi tiết tại [crawlers/README.md](crawlers/README.md).

```bash
# Cài đặt thư viện crawler
pip install httpx pandas playwright beautifulsoup4
playwright install chromium

# Cào dữ liệu tuyển dụng VietnamWorks
python crawlers/vietnamworks/run.py

# Cào dữ liệu tuyển dụng ITviec
python crawlers/itviec/run.py
```

### 2. Phân Hệ Xử Lý Dữ Liệu & Kiểm Thử (Pipeline)
Xem hướng dẫn chi tiết tại [pipeline/README.md](pipeline/README.md).

```bash
# Cài đặt thư viện pipeline
pip install -r pipeline/requirements.txt

# Chạy bộ kiểm thử tự động 20 Test Suites
python -m unittest pipeline/test_recruitment_pipeline.py

# Chạy thử nghiệm pipeline trên bộ dữ liệu mẫu 50 dòng
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

## ⚖️ Giấy Phép & Chính Sách Gỡ Dữ Liệu (Takedown Policy)

- **Mã nguồn:** Toàn bộ mã nguồn thu thập và xử lý dữ liệu được phát hành theo giấy phép [MIT License](LICENSE).
- **Dữ liệu công bố:** Dữ liệu trong thư mục `data/dashboard/` và `manual_overrides/` là các chỉ số thống kê, bảng tổng hợp phân tích và metadata đã qua xử lý (chức danh, tên công ty, thành phố, khoảng lương, cấp bậc, nhãn kỹ năng). Dự án **không lưu trữ và không phân phối lại** văn bản mô tả công việc (JD Description) hoặc yêu cầu chi tiết (Job Requirements) của nhà tuyển dụng.
- **Yêu cầu gỡ bỏ thông tin (Data Takedown):** Nếu doanh nghiệp tuyển dụng hoặc các nền tảng có bất kỳ quan ngại nào liên quan đến dữ liệu định danh hoặc mong muốn gỡ bỏ thông tin, xin vui lòng tạo thông báo tại mục **GitHub Issues** của kho lưu trữ. Chúng tôi sẽ tiếp nhận và tiến hành cập nhật bộ từ điển loại trừ trong vòng 48 giờ làm việc.
