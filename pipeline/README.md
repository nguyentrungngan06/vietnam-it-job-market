# HR Market Intelligence Pipeline: IT Recruitment Vietnam

Phân hệ Data Pipeline xử lý, làm sạch, chuẩn hóa, phân loại kỹ năng 2 tầng, bóc tách mức lương đa chiều, khử trùng lặp có luật bảo vệ chống nối chuỗi (Guard Rule Deduplication) và dựng mô hình Star Schema phục vụ phân tích thị trường việc làm IT tại Việt Nam.

> [!NOTE]
> **Phạm vi dữ liệu:** Bộ dữ liệu quan sát được thu thập từ 2 nền tảng tuyển dụng (**ITviec** và **VietnamWorks**) trong giai đoạn từ **10/10/2026 đến 25/10/2026** (khoảng 2.000 tin tuyển dụng). Tập dữ liệu phản ánh lát cắt quan sát trong khoảng thời gian này trên 2 nền tảng nêu trên và không đại diện cho toàn bộ thị trường lao động công nghệ tại Việt Nam.

---

## 1. Cấu Trúc Phân Hệ Pipeline

```text
pipeline/
├── recruitment_pipeline.py      # Module xử lý cốt lõi: Làm sạch, map kỹ năng, khử trùng lặp
├── dashboard_data.py            # Module tạo mô hình Star Schema & tính toán chỉ số
├── run_hr_pipeline.py           # Script điều phối chạy quy trình từ dòng lệnh
├── test_recruitment_pipeline.py # Bộ kiểm thử tự động 21 Suites kiểm tra bất biến dữ liệu
├── requirements.txt             # Khai báo thư viện phụ thuộc (rapidfuzz, pandas, openpyxl)
├── quality_report.json          # Báo cáo đo lường chất lượng dữ liệu và các giả định quy đổi
└── README.md                    # Tài liệu kỹ thuật chi tiết của phân hệ
```

---

## 2. Các Cải Tiến Xử Lý Dữ Liệu

### 2.1. Khử Trùng Lặp Có Luật Bảo Vệ (Guard Rule Deduplication)
- **Vấn đề nhận diện:** Phương pháp so khớp fuzzy đơn thuần dễ gây gộp nhầm các tin tuyển dụng khác vị trí (ví dụ: các vị trí cùng công ty nhưng khác cấp bậc năm kinh nghiệm hoặc khác phân mảng).
- **Luật bảo vệ (Guard Rule):** Một tin bản sao chỉ được tự động gộp vào tin bản chính khi thỏa mãn đồng thời:
  1. Độ phủ văn bản đoạn ngắn trong đoạn dài: $\text{text\_containment} \ge 90\%$.
  2. Số năm kinh nghiệm tối thiểu tương thích (`exp_min_1 == exp_min_2` hoặc một bên chưa xác định).
- **Chống nối chuỗi bắc cầu (Anti-Transitive Chaining):**
  - Mọi tin bản sao khi gom cụm bắt buộc phải thỏa mãn luật bảo vệ trực tiếp với bản chính (`Primary Job`).
  - Cột `duplicate_of_uid` luôn trỏ trực tiếp đến `main_uid`, đảm bảo mỗi nhóm chỉ có duy nhất một bản chính.
- **Kiểm định độc lập:**
  - Mẫu kiểm toán 20 cặp ban đầu: 15 cặp trùng thực tế, 4 cặp gộp nhầm được luật bảo vệ phát hiện và ngăn chặn thành công, 1 cặp biên.
  - **Kiểm định độc lập bổ sung trên 30 cặp tin mới** (`duplicate_validation_sample_30.csv`): 30/30 cặp (100%) đạt luật bảo vệ và được đối soát thủ công xác nhận là tin trùng thực tế.

### 2.2. Chuẩn Hóa Bảng Lương (`salary_benchmarks.csv`)
- **Tách bạch bản chất các loại số liệu:**
  - Tin có khoảng lương (`range` & `exact`): Đủ điều kiện tính trung vị, P25, P75.
  - Tin mức sàn ("Từ X" - `from`): Tính trung vị mức tối thiểu.
  - Tin mức trần quảng cáo ("Tới X" - `up_to`): Là mức ngân sách tối đa được đăng tin, không phản ánh lương chi trả kỳ vọng và được phân tách riêng.
- **Xử lý cỡ mẫu nhỏ ($n < 5$):** Khi số lượng tin thuộc phân khúc $n_{\text{range}} < 5$, các giá trị `median_range_mid_m`, `p25`, `p75` được gán về `NaN` để tránh gây sai lệch trực quan. Hiện có **27 / 96 ô** phân khúc đạt $n_{\text{range}} \ge 5$.
- **Khai thác cấp bậc suy luận (`level_inferred_exp`):** Khi chức danh không nêu rõ cấp bậc, pipeline sử dụng số năm kinh nghiệm yêu cầu để suy luận. Tỷ lệ cấp bậc `unknown` giảm từ 57% xuống còn **11.69%** (236/2.019 tin).
- **Phân loại vai trò chuyên môn:** Hệ luật regex nhận diện 20 vai trò kỹ thuật giúp giảm tỷ lệ nhóm `other` từ 40% xuống còn **26.80%** (541/2.019 tin).

### 2.3. Minh Bạch Chất Lượng Mô Tả & Cắt Cụt Thời Gian
- **Phân loại chất lượng văn bản (`text_quality`):**
  - `full` (1.583 / 2.019 tin, chiếm 78.4%): Gồm 968 tin ITviec ($\ge 400$ ký tự) và 618 tin VietnamWorks được làm giàu chi tiết ($\ge 800$ ký tự).
  - `truncated` (436 tin): Tin VietnamWorks trích dẫn tóm tắt chưa được làm giàu.
- **Nhận diện cắt cụt thời gian (Left & Right Censored):**
  - `left_censored`: Tin đã xuất hiện ngay ở snapshot đầu tiên (10-11/10/2026), không rõ thời điểm mở tuyển thực tế.
  - `right_censored`: Tin vẫn đang mở tuyển tại ngày snapshot cuối cùng (25/10/2026).
  - *Lưu ý:* Trường `days_active` chỉ phản ánh số ngày quan sát thấy trong chu kỳ 15 ngày, không phải tổng thời gian mở tuyển thực tế (time-to-hire).

### 2.4. Chuẩn Hóa Nhóm Vị Trí Đa Nguồn (Role Group Classification)
- **Bối cảnh & Sai khác Schema giữa hai sàn:**
  - Trên tổng số 1.884 tin tuyển dụng hợp lệ sau khử trùng lặp (`valid_job`), ITviec đóng góp **927 tin (49.20%)** và VietnamWorks đóng góp **957 tin (50.80%)**.
  - Sàn ITviec có khoảng 20 trường rỗng 100% so với VietnamWorks (`job_function`, `level`, `views`, `days_alive`, `industry`, `posted_on`, `expired_on`...). Cột `job_function` gốc của VietnamWorks phân loại quá thô (ví dụ gom chung Backend/Frontend/Mobile thành "Software Developer") và hoàn toàn vắng bóng ở ITviec.
  - Do đó, pipeline thiết lập bộ nhận diện vị trí chuẩn tắc dựa trên `title` (đạt 100% độ phủ ở cả hai sàn), kết hợp fallback qua kỹ năng yêu cầu (`skills`) và phân ngành phụ trợ (`job_function` của VietnamWorks).
- **Hệ thống 15 nhóm vị trí chuẩn (`role_group`):**
  - `Backend` (256 tin - 13.59%), `Data / AI` (286 tin - 15.18%), `BA / PO / PM` (242 tin - 12.85%), `DevOps / Cloud / SysAdmin` (156 tin - 8.28%), `QA / QC / Tester` (148 tin - 7.86%), `Security` (105 tin - 5.57%), `Fullstack` (95 tin - 5.04%), `IT Support / ERP` (66 tin - 3.50%), `Embedded / Hardware / Telecom` (36 tin - 1.91%), `Mobile` (29 tin - 1.54%), `Frontend` (24 tin - 1.27%), `Management / Leadership` (23 tin - 1.22%), `Game Dev` (14 tin - 0.74%), `UI / UX Design` (14 tin - 0.74%), `Other` (390 tin - 20.70%).
- **Kiểm soát ranh giới nghiêm ngặt:**
  - *Data / AI*: Đặt ranh giới từ khóa chặt chẽ (`data scientist`, `machine learning`, `data engineer`, `etl`, `bi analyst`, `dba`...), loại trừ các title lạm phát và tránh fallback nhầm từ các kỹ năng cơ sở dữ liệu phổ thông (`SQL`, `PostgreSQL`).
  - *Management / Leadership*: Chỉ gom các vị trí C-level và quản lý IT cấp cao (`CTO`, `CIO`, `Head of IT`, `IT Director`...), giữ các vị trí quản lý chuyên môn (`QA Manager`, `Cybersecurity Manager`, `Data Science Manager`) đúng về nhóm nghiệp vụ tương ứng.
- **Minh bạch nguồn gốc & độ tin cậy:**
  - `role_source`: `title` (1.363 tin - 72.35%), `unknown` (390 tin - 20.70%), `job_function` (112 tin - 5.94%), `skills` (19 tin - 1.01%).
  - `role_confidence`: `high` (1.306 tin - 69.32%), `medium` (131 tin - 6.95%), `low` (447 tin - 23.73%).
- **Kiểm định độc lập trên mẫu ngẫu nhiên:** Kiểm toán mù 100 tin ngẫu nhiên (`random_state=42`) ghi nhận độ chính xác thực tế đạt **96.0%** (96/100 tin phân loại chuẩn xác).

---

## 3. Chỉ Số Nhu Cầu Kỹ Năng (`skill_demand_index`)

Chỉ số nhu cầu kỹ năng (thang 0–100) được tính theo trọng số chuẩn hóa bách phân vị:

$$\text{Index} = 100 \times \left( 0.45 \times P_{\text{job}} + 0.35 \times P_{\text{company}} + 0.20 \times S_{\text{required}} \right)$$

- $P_{\text{job}}$: Thứ hạng bách phân vị theo số lượng tin tuyển dụng (45%).
- $P_{\text{company}}$: Thứ hạng bách phân vị theo số lượng doanh nghiệp tuyển dụng (35%).
- $S_{\text{required}}$: Tỷ lệ yêu cầu mang tính bắt buộc so với tổng tin nhắc đến kỹ năng (20%).

**Phân tích độ nhạy (Sensitivity Analysis):** Pipeline tính kèm kịch bản Cân bằng $(0.34, 0.33, 0.33)$ và kịch bản Thiên lượng tin $(0.60, 0.25, 0.15)$. Hệ số tương quan thứ hạng Spearman giữa các kịch bản đạt $r_s > 0.98$, cho thấy bảng xếp hạng top kỹ năng duy trì tính ổn định cao.

---

## 4. Từ Điển Dữ Liệu Các Bảng Mart

### 4.1. Bảng `data/dashboard/fact_jobs.csv`
Bảng cấp tin tuyển dụng đã loại bỏ toàn bộ văn bản mô tả dài, chỉ lưu trữ metadata đã chuẩn hóa:
- `job_uid`: Mã định danh tin tuyển dụng (`itviec:<id>` hoặc `vietnamworks:<id>`).
- `site`: Nguồn thu thập (`itviec` hoặc `vietnamworks`).
- `title`: Tiêu đề công việc đã chuẩn hóa khoảng trắng.
- `company_canonical_name`: Tên doanh nghiệp đã chuẩn hóa tên pháp nhân.
- `city`: Địa phương chuẩn hóa tiếng Việt có dấu.
- `role_group`: 15 nhóm vị trí chuẩn hóa chuẩn BI (Backend, Frontend, Fullstack, Mobile, Data / AI, DevOps...).
- `role_source`: Nguồn suy luận nhãn vị trí (`title`, `job_function`, `skills`, `unknown`).
- `role_confidence`: Độ tin cậy gán nhãn (`high`, `medium`, `low`).
- `role_dashboard`: Phân loại vai trò chi tiết (backward compatible).
- `level_dashboard`: Cấp bậc chuẩn hóa (kết hợp tiêu đề và kinh nghiệm).
- `salary_type_norm`: Loại lương (`range`, `exact`, `from`, `up_to`, `negotiable`, `unknown`).
- `salary_min_m`, `salary_max_m`, `salary_mid_m`: Mức lương quy đổi triệu VND/tháng.
- `salary_reliable`: Cờ độ tin cậy của thông tin lương.
- `text_source`: Nguồn nội dung (`itviec_snapshot`, `vietnamworks_enriched`, `vietnamworks_snapshot_truncated`).
- `text_quality`: Đánh giá độ đầy đủ mô tả (`full` hoặc `truncated`).
- `left_censored`, `right_censored`: Cờ đánh dấu biên thời gian quan sát.

### 4.2. Bảng `data/dashboard/salary_benchmarks.csv`
Bảng chuẩn mực lương theo phân khúc vai trò $\times$ cấp bậc:
- `role_group`, `level_dashboard`: Cặp phân khúc vai trò chuẩn và cấp bậc.
- `n_salary_jobs`: Tổng số tin tuyển dụng có thông tin lương hợp lệ.
- `n_range_jobs`: Cỡ mẫu tin khoảng lương đủ điều kiện tính toán ($n_{\text{range}}$).
- `median_range_mid_m`, `p25_range_mid_m`, `p75_range_mid_m`: Trung vị và phân vị khoảng lương (gán `NaN` khi $n_{\text{range}} < 5$).
- `median_floor_from_m`: Trung vị mức sàn của các tin "Từ X" ($n \ge 5$).
- `median_ceiling_upto_m`: Trung vị mức trần quảng cáo của các tin "Tới X" ($n \ge 5$).
- `sample_warning_range`: Cảnh báo cỡ mẫu nhỏ ($n_{\text{range}} < 5$).

---

## 5. Hướng Dẫn Chạy Thử Với Dữ Liệu Mẫu

Cài đặt thư viện:
```bash
pip install -r requirements.txt
```

Chạy bộ kiểm thử tự động 21 Test Suites:
```bash
python -m unittest test_recruitment_pipeline.py
```

Chạy pipeline kiểm thử trên tập dữ liệu mẫu 50 dòng (`data/sample/`):
```bash
python run_hr_pipeline.py --input ../data/sample/itviec_sample.csv ../data/sample/vietnamworks_sample.csv --out ../scratch/sample_output
```

---

## 6. Tuyên Bố Bản Quyền & Yêu Cầu Gỡ Dữ Liệu (Takedown Policy)

- **Nguồn dữ liệu gốc:** Dữ liệu tuyển dụng được thu thập từ các tin đăng công khai trên nền tảng ITviec và VietnamWorks nhằm phục vụ mục đích nghiên cứu học thuật và phân tích thị trường lao động.
- **Bảo vệ bản quyền:** Dự án cam kết không lưu trữ, không phân phối lại văn bản mô tả công việc (JD Description) hoặc yêu cầu chi tiết (Job Requirements). Các tệp dữ liệu công bố tại kho lưu trữ chỉ bao gồm các trường metadata đã qua xử lý, làm sạch và tổng hợp thống kê.
- **Quy trình yêu cầu gỡ bỏ:** Nếu bất kỳ đơn vị tuyển dụng hoặc nền tảng nào có nguyện vọng gỡ bỏ thông tin liên quan đến doanh nghiệp hoặc tin tuyển dụng của mình, vui lòng gửi yêu cầu qua mục **GitHub Issues** của kho lưu trữ. Chúng tôi sẽ tiếp nhận và tiến hành cập nhật bộ từ điển loại trừ hoặc gỡ bản ghi trong vòng 48 giờ làm việc.
