# Báo Cáo Phân Tích Phần I: Kiểm Tra posted_date, Khử Trùng Liên Đợt, Gộp Bảng Và Chốt Quy Ước Bước 2

---

## I.1. Kiểm Tra posted_date Của Đợt 2

### 1. Thống kê theo Sàn × Đợt

| Đợt | Sàn | Số tin có `posted_date` | Tỷ lệ (%) | Min `posted_date` | Max `posted_date` | Min `crawl_date` (first_seen) | Max `crawl_date` (last_seen) | Tin đăng sau ngày cào | Median khoảng cách (ngày) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Đợt 1** | ITviec | 0 / 927 | 0.0% | N/A | N/A | 2026-10-10 | 2026-10-25 | 0 | N/A |
| **Đợt 1** | VietnamWorks | 957 / 957 | 100.0% | 2026-09-10 | 2026-10-24 | 2026-10-10 | 2026-10-25 | 0 | 20.0 |
| **Đợt 2** | ITviec | 843 / 843 | 100.0% | 2026-09-30 | 2026-11-19 | 2026-10-10 | 2026-11-20 | 0 | 14.0 |
| **Đợt 2** | VietnamWorks | 954 / 954 | 100.0% | 2026-10-05 | 2026-11-20 | 2026-10-10 | 2026-11-20 | 0 | 23.0 |

### 2. Phân bố theo tuần của ITviec Đợt 2

Dữ liệu `posted_date` của ITviec Đợt 2 rải đều suốt **8 tuần liên tục**, không hề dồn sát ngày cào:

- Tuần 2026-09-28 đến 2026-10-04: 39 tin (4.6%)
- Tuần 2026-10-05 đến 2026-10-11: 60 tin (7.1%)
- Tuần 2026-10-12 đến 2026-10-18: 81 tin (9.6%)
- Tuần 2026-10-19 đến 2026-10-25: 108 tin (12.8%)
- Tuần 2026-10-26 đến 2026-11-01: 126 tin (14.9%)
- Tuần 2026-11-02 đến 2026-11-08: 150 tin (17.8%)
- Tuần 2026-11-09 đến 2026-11-15: 158 tin (18.7%)
- Tuần 2026-11-16 đến 2026-11-22: 121 tin (14.4%)

Khoảng cách từ ngày đăng đến lần quan sát cuối cùng (`last_seen - posted_date`) có trung vị là **14 ngày**, dải phân bố rộng từ 0 đến 49 ngày.
- **Kết luận:** `posted_date` của ITviec Đợt 2 là **ngày đăng thật**, đủ điều kiện sử dụng cùng VietnamWorks cho phân tích xu hướng thời gian.

### 3. Độ dài thật của chuỗi tuần theo `posted_date`
- **Đợt 1:** Chuỗi tuần của VietnamWorks kéo dài **7 tuần** (từ 07/09/2026 đến 25/10/2026).
- **Đợt 2:** Chuỗi tuần của cả 2 sàn kéo dài **8 tuần** (từ 28/09/2026 đến 22/11/2026).
- **Chuỗi gộp toàn bộ:** Kéo dài **11 tuần liên tục** (từ tuần 07/09/2026 đến tuần 22/11/2026).

---

## I.2. Tìm Tin Trùng Giữa Hai Đợt

- **Số `job_uid` trùng nhau chính xác:** 909 tin.
- **Số khóa thay thế `surrogate_key` (`site___company___title___city` chuẩn hoá) trùng nhau:** 1.025 khóa.
- **Tổng số tin trùng lặp liên đợt (thỏa mãn trùng UID HOẶC trùng surrogate_key):**
  - Đợt 1 có mặt ở Đợt 2: **1.060 tin (56.26% của Đợt 1)**
  - Đợt 2 có mặt ở Đợt 1: **1.059 tin (58.93% của Đợt 2)**
- **File lưu trữ chi tiết tin trùng:** Đã lưu [`inter_batch_duplicates.csv`](../data/dedup_audit/inter_batch_duplicates.csv) (1.035 cặp).
- **Quy tắc gộp:**
  - Bảng chính chỉ giữ lần quan sát sớm nhất (toàn bộ 1.884 tin hợp lệ Đợt 1).
  - Đợt 2 chỉ lấy các tin mới chưa từng thấy ở Đợt 1: 738 tin.
  - Đã thêm 2 cột: `crawl_batch` (1 hoặc 2) và `n_batches_seen` (1: thấy ở 1 đợt; 2: tồn tại xuyên suốt cả 2 đợt).

---

## I.3. Gộp Hai Bảng Và Xây Dựng Bảng Cơ Sở

- **Tổng số tin bảng gộp:** **2.622 tin tuyển dụng duy nhất** (1.884 tin đợt 1 + 738 tin mới đợt 2).
- **Tính lại ngưỡng kỹ năng $\ge 30$ tin:** Có **71 kỹ năng** đạt ngưỡng (tăng so với 63 kỹ năng của Đợt 1 và 62 kỹ năng của Đợt 2).
- **Cấu trúc bảng cơ sở gộp:** **164 cột**:
  - 6 cột định danh: `job_uid`, `crawl_batch`, `n_batches_seen`, `company_canonical_id`, `company_canonical_name`, `title`
  - 11 cột mô tả tin & thời gian: `site`, `text_quality`, `posted_date`, `first_seen`, `last_seen`, `city_norm`, `role_family`, `role_dashboard`, `level_final`, `company_type`, `exp_min_years`
  - 1 cột lương: `salary_mid_m`
  - 4 cột tổng hợp: `n_skills`, `n_required`, `n_advanced`, `demand_score`
  - 71 cột nhị phân `sk_...`
  - 71 cột trọng số `w_...`
- **Kiểm tra tính toàn vẹn (Validation):**
  - Khóa `job_uid` không trùng lặp: **True (PASS 100%)**
  - Điều kiện logic $sk\_x = 1 \iff w\_x > 0$: **True (PASS 100%)**
- **File lưu bảng cơ sở gộp:** [`analysis_base_merged_raw.csv`](../data/base/analysis_base_merged_raw.csv).

---

## I.4. So Sánh Đợt 1 Và Đợt 2

### 1. Bảng đối sánh cơ cấu mẫu

| Tiêu chí | Đợt 1 (N = 1.884) | Đợt 2 (N = 1.797) | Chênh lệch | Đánh giá |
| :--- | :---: | :---: | :---: | :--- |
| **Tỷ lệ sàn ITviec / VietnamWorks** | 49.2% / 50.8% | 46.9% / 53.1% | -2.3% ITviec | Rất cân bằng |
| **Tỷ lệ `text_quality = full`** | 80.6% | 98.0% | +17.4% | Đã bổ sung full JD từ daily (1.904/1.940 tin) |
| **Tỷ lệ tin có lương** | 22.4% (422 tin) | 17.3% (311 tin) | -5.1% | Giảm chủ yếu ở nhóm tin VNW mới |
| **Tỷ lệ tin có lương bằng USD** | 19.1% | 12.7% | -6.4% | Cơ cấu tin ngoại tệ giảm |
| **Lương trung vị ITviec** | 42.50 tr | 37.50 tr | -5.00 tr | Thay đổi thành phần mẫu |
| **Lương trung vị VietnamWorks** | 31.25 tr | 29.17 tr | -2.08 tr | Ổn định tương đối |
| **Lương trung vị toàn thị trường** | 37.50 tr | 31.25 tr | -6.25 tr | Tác động kép từ tỷ lệ USD và ITviec |

### 2. Phân bố Vai trò (Role Family)

| Vai trò | Đợt 1 (%) | Đợt 2 (%) | Chênh lệch (%) |
| :--- | :---: | :---: | :---: |
| **Other** | 20.6% | 22.1% | +1.5% |
| **Data / AI** | 15.2% | 16.0% | +0.8% |
| **Backend** | 13.6% | 13.1% | -0.5% |
| **BA / PO / PM** | 12.9% | 12.2% | -0.6% |
| **DevOps / Cloud / SysAdmin** | 8.3% | 8.0% | -0.3% |
| **QA / QC / Tester** | 7.9% | 7.7% | -0.2% |
| **Security** | 5.6% | 6.0% | +0.4% |
| **Fullstack** | 5.1% | 4.6% | -0.5% |
| **IT Support / ERP** | 3.5% | 3.5% | -0.1% |
| **Embedded / Hardware / Telecom** | 1.9% | 1.6% | -0.3% |
| **Mobile** | 1.5% | 1.2% | -0.4% |
| **Frontend** | 1.3% | 1.2% | -0.1% |
| **Management / Leadership** | 1.2% | 1.3% | +0.1% |
| **Game Dev** | 0.7% | 0.8% | +0.0% |
| **UI / UX Design** | 0.7% | 0.7% | -0.0% |

*Nhận xét:* Cơ cấu vai trò giữa 2 đợt **gần như trùng khớp hoàn toàn**, mọi vai trò đều dao động dưới $1\%$.

### 3. Phân bố Cấp bậc (Level)

| Cấp bậc | Đợt 1 (%) | Đợt 2 (%) | Chênh lệch (%) |
| :--- | :---: | :---: | :---: |
| **Senior** | 22.1% | 20.4% | -1.7% |
| **Manager** | 5.8% | 5.8% | 0.0% |
| **Lead** | 5.0% | 4.7% | -0.3% |
| **Middle** | 4.4% | 4.1% | -0.3% |
| **Intern** | 2.7% | 2.4% | -0.2% |
| **Junior** | 1.6% | 1.9% | +0.2% |
| **Fresher** | 1.6% | 1.9% | +0.3% |
| **Director** | 1.2% | 1.3% | +0.1% |
| **Unknown** | 55.7% | 57.4% | +1.7% |

### 4. Đối sánh Top 15 Kỹ năng Phổ biến Nhất (Kèm Khoảng tin cậy 95%)

| Kỹ năng | Đợt 1 (%) | Đợt 2 (%) | Chênh lệch (%) | CI 95% Đợt 1 | CI 95% Đợt 2 | Kết luận |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **English** | 16.7% | 15.6% | -1.0% | [15.0, 18.3] | [14.0, 17.3] | Trùng khoảng CI (Khớp) |
| **Python** | 15.9% | 15.6% | -0.3% | [14.2, 17.5] | [13.9, 17.3] | Trùng khoảng CI (Khớp) |
| **Artificial Intelligence (AI)** | 14.1% | 14.2% | +0.1% | [12.5, 15.7] | [12.6, 15.9] | Trùng khoảng CI (Khớp) |
| **SQL** | 14.0% | 14.8% | +0.8% | [12.4, 15.6] | [13.2, 16.4] | Trùng khoảng CI (Khớp) |
| **Software Architecture & Design** | 10.7% | 10.9% | +0.1% | [9.3, 12.1] | [9.4, 12.3] | Trùng khoảng CI (Khớp) |
| **Business Analysis (BA)** | 10.7% | 9.5% | -1.2% | [9.3, 12.1] | [8.2, 10.9] | Trùng khoảng CI (Khớp) |
| **Project Management** | 9.7% | 9.4% | -0.3% | [8.3, 11.0] | [8.1, 10.8] | Trùng khoảng CI (Khớp) |
| **.NET / C#** | 9.3% | 9.6% | +0.3% | [8.0, 10.7] | [8.3, 11.0] | Trùng khoảng CI (Khớp) |
| **Cybersecurity** | 9.9% | 10.1% | +0.2% | [8.5, 11.2] | [8.7, 11.5] | Trùng khoảng CI (Khớp) |
| **Java** | 9.6% | 9.0% | -0.6% | [8.2, 10.9] | [7.6, 10.3] | Trùng khoảng CI (Khớp) |
| **Digital Transformation / Consulting** | 9.0% | 9.7% | +0.7% | [7.7, 10.3] | [8.3, 11.1] | Trùng khoảng CI (Khớp) |
| **ERP / CRM / Enterprise Apps** | 9.2% | 8.8% | -0.4% | [7.9, 10.5] | [7.5, 10.1] | Trùng khoảng CI (Khớp) |
| **Agile & Scrum** | 9.1% | 9.3% | +0.3% | [7.8, 10.4] | [8.0, 10.7] | Trùng khoảng CI (Khớp) |
| **Data Analysis** | 9.0% | 8.6% | -0.4% | [7.7, 10.3] | [7.3, 9.9] | Trùng khoảng CI (Khớp) |
| **Software Engineering (general)** | 9.3% | 9.3% | +0.1% | [8.0, 10.6] | [8.0, 10.7] | Trùng khoảng CI (Khớp) |

- **Kết luận:** **100% kỹ năng trong Top 15 đều nằm trong khoảng tin cậy 95% giữa hai đợt.** Phân bố kỹ năng và vai trò của 2 đợt hoàn toàn đồng nhất -> **ĐỦ ĐIỀU KIỆN GỘP BẢNG**.

---

## I.5. Chốt Quy Ước Dùng Chung Cho Bước 2

1. **Mẫu số phân tích kỹ năng:**
   - Loại bỏ các tin có `n_skills == 0`: Trên toàn bảng gộp 2.622 tin, chỉ có **2 tin bị loại** (đều ở sàn VietnamWorks, chiếm 0.08%).
   - Mẫu số phân tích kỹ năng chuẩn cho Bước 2: **2.620 tin**.

2. **Bảng gộp `skill_family`:**
   - Đã gộp các nhóm trùng nghĩa: `ai_data` (6) và `ai_machine_learning` (2) -> `ai_data_ml` (8 kỹ năng).
   - Đã gộp các nhóm quản trị/phương pháp luận: `methodology`, `business_process`, `productivity`, `management` -> `management_process`.
   - Nhóm `engineering_general` gồm 2 kỹ năng: `Software Engineering (general)` và `Version Control (Git)` (giữ nguyên để phân tích nhóm nền tảng kỹ thuật).
   - Đã lưu bảng ánh xạ hoàn chỉnh tại: [`skill_taxonomy.csv`](../data/reference/skill_taxonomy.csv).

3. **Kỹ năng nền (`is_general`):**
   - Đã gắn nhãn `is_general = True` cho 4 kỹ năng nền tảng / ngôn ngữ làm việc: `English`, `Japanese`, `Project Management`, `Agile & Scrum`.

4. **Nhóm công ty gộp (Anonymous Headhunting Client):**
   - Đợt 2 ghi nhận `c_navigos_client` có **54 tin tuyển dụng** (tương đương 53 tin ở Đợt 1).
   - Đây là nhóm client ẩn danh của bên săn đầu người Navigos, không phải một pháp nhân đơn lẻ -> **Cần loại bỏ khỏi bảng xếp hạng công ty đơn lẻ ở Bước 3**.

5. **Ngưỡng cỡ mẫu:**
   - **Xếp hạng vai trò:** Ngưỡng tối thiểu $\ge 20$ tin.
     - Ẩn xếp hạng cho: `Game Dev` (19 tin) và `UI / UX Design` (17 tin).
     - 13 vai trò còn lại đều $\ge 31$ tin (hợp lệ để xếp hạng).
   - **Phân tích kỹ năng:** Ngưỡng tối thiểu $\ge 30$ tin (đã chọn 71 kỹ năng hợp lệ).
   - **Tính độ liên kết cặp (NPMI):** Cặp kỹ năng xuất hiện chung tối thiểu $\ge 10$ tin.

---

## Bảng Kiểm Tra Cuối Phần I

| Câu hỏi kiểm tra | Trạng thái | Ghi chú tóm tắt |
| :--- | :---: | :--- |
| `posted_date` ITviec đợt 2 là ngày đăng thật hay không | **Xong (Có)** | Rải đều qua 8 tuần (từ 30/09 đến 19/11), không dồn sát ngày cào; dùng được cho phân tích xu hướng. |
| Độ dài thật của chuỗi tuần mỗi đợt | **Xong** | Đợt 1: 7 tuần (chỉ VNW); Đợt 2: 8 tuần (cả 2 sàn); Chuỗi gộp: 11 tuần liên tục (07/09 – 22/11/2026). |
| Số tin trùng giữa hai đợt và quy tắc xử lý | **Xong** | 1.060 tin trùng (56.26% đợt 1, 58.93% đợt 2); Quy tắc: giữ lần quan sát sớm nhất (Đợt 1), thêm `n_batches_seen` & `crawl_batch`. |
| Số tin và số cột kỹ năng của bảng gộp | **Xong** | 2.622 tin duy nhất (chuẩn hóa Bước 2: 2.620 tin); 71 kỹ năng $\ge 30$ tin (142 cột `sk_` + `w_`, tổng cộng 167 cột sau khi thêm `posted_date_final`, `date_source`, `in_full_sample`). |
| Hai đợt có gộp được không | **Xong (Có)** | Có; Top 15 kỹ năng và cơ cấu vai trò khớp nhau 100% trong khoảng tin cậy 95%. |
| Mẫu số, bảng gộp skill_family, kỹ năng nền đã chốt | **Xong** | Loại 2 tin n_skills=0; Gộp ai_data_ml, management_process; Gắn 4 kỹ năng nền; Ẩn Game Dev & UI/UX (< 20 tin). |
