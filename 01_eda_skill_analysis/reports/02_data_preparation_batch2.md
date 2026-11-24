# Báo Cáo Thực Hiện Bước 0: Tạo Bảng Cơ Sở `analysis_base_tu_sau_25_10.csv`

## 1. Mục Tiêu & Dữ Liệu Đầu Vào
Tạo bảng cơ sở `analysis_base_tu_sau_25_10.csv` chuẩn hoá và làm sạch cho đợt dữ liệu từ sau 25/10 (tháng 11/2026), mỗi dòng là một tin tuyển dụng duy nhất, đầy đủ các trường thông tin cần thiết phục vụ các phân tích tiếp theo.

- **Nguồn dữ liệu:**
  - `hr_pipeline_output_tu_sau_25_10/clean/combine_clean.csv` (1,940 dòng gốc)
  - `hr_pipeline_output_tu_sau_25_10/dashboard/fact_job_skills.csv` (7,970 dòng kỹ năng)
- **Cột khoá nối:** `job_uid`

---

## 2. Quy Trình Xử Lý Chi Tiết

### 2.1. Lọc bỏ tin trùng (Deduplication)
- Giữ các dòng thoả điều kiện: `is_duplicate == False`.
- Kết quả: Giữ lại **1,797** tin tuyển dụng hợp lệ (loại bỏ 143 tin trùng lặp nội bộ và chéo sàn).

### 2.2. Tính lương trung tâm `salary_mid_m`
- Thỏa mãn 3 điều kiện:
  1. `salary_type_norm` thuộc `range` hoặc `exact`.
  2. `salary_needs_review` là `False`.
  3. Giá trị lương > 0.
- Kết quả:
  - Tổng số tin có lương: **311** tin (17.3%).
  - Trung vị lương ITviec: **37.50** triệu VNĐ.
  - Trung vị lương VietnamWorks: **29.17** triệu VNĐ.
  - Trung vị chung toàn thị trường: **31.25** triệu VNĐ.

### 2.3. Gắn vai trò và cấp bậc
- Nối từ `fact_job_skills` (rút gọn 1 dòng / `job_uid`).
- `role_family`: từ `role_group` (rỗng điền 'Other').
- `level_final`: ưu tiên `level_norm`, fallback `level_dashboard`, còn lại `'unknown'`.
- Kết quả: **171** tin có cấp bậc `'unknown'` (9.5%).

### 2.4. Thành phố và loại công ty
- `city_norm`: chuẩn hóa từ `city`, null điền `'Khác'`.
- `company_type`: khởi tạo cột trống chuẩn bị cho phân loại.

### 2.5. Xử lý các cột kỹ năng
- Lấy các dòng `valid_job == True` từ `fact_job_skills`.
- **Top 62 kỹ năng:** xuất hiện trong $\ge 30$ tin tuyển dụng.
  - `sk_<tên_kỹ_năng>`: biến nhị phân (0 hoặc 1).
  - `w_<tên_kỹ_năng>`: biến trọng số tương ứng `imp_weight` cao nhất.
- **4 cột tổng hợp:**
  - `n_skills`: số kỹ năng độc nhất của tin.
  - `n_required`: số kỹ năng có `importance == 'required'`.
  - `n_advanced`: số kỹ năng có `proficiency == 'advanced'`.
  - `demand_score`: tổng trọng số nhu cầu `imp_weight`.

### 2.6. Cấu trúc cột của `analysis_base_tu_sau_25_10.csv` (142 cột)
1. **Định danh (4 cột):** `job_uid`, `company_canonical_id`, `company_canonical_name`, `title`
2. **Mô tả tin (9 cột):** `site`, `text_quality`, `posted_date`, `city_norm`, `role_family`, `role_dashboard`, `level_final`, `company_type`, `exp_min_years`
3. **Lương (1 cột):** `salary_mid_m`
4. **Tổng hợp (4 cột):** `n_skills`, `n_required`, `n_advanced`, `demand_score`
5. **Kỹ năng nhị phân (62 cột):** `sk_...`
6. **Kỹ năng trọng số (62 cột):** `w_...`

---

## 3. Bảng Đối Soát Tính Toàn Vẹn (Validation Checklist)

| Chỉ tiêu kiểm tra | Kết quả thực tế | Trạng thái |
| :--- | :--- | :---: |
| Số dòng hợp lệ | **1,797** dòng | **PASS** |
| `job_uid` duy nhất (không trùng) | **100% Unique** (1,797) | **PASS** |
| Số tin có lương tính được | **311** (17.3%) | **PASS** |
| Lương trung vị ITviec | **37.50** triệu VNĐ | **PASS** |
| Lương trung vị VietnamWorks | **29.17** triệu VNĐ | **PASS** |
| Số công ty có $\ge 5$ tin | **74** công ty | **PASS** |
| Số tin có `posted_date` | **1,797** tin (100.0%) | **PASS** |
| Tổng số cột | **142** cột (18 base + 62 sk_ + 62 w_) | **PASS** |
| Logic $sk\_x = 1 \iff w\_x > 0$ | **Đúng 100% dòng** | **PASS** |
