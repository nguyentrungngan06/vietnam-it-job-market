# Báo Cáo Thực Hiện Bước 0: Tạo Bảng Cơ Sở `analysis_base.csv`

## 1. Mục Tiêu & Dữ Liệu Đầu Vào
Tạo bảng duy nhất `analysis_base.csv` chuẩn hoá và làm sạch, mỗi dòng là một tin tuyển dụng duy nhất, đầy đủ các trường thông tin cần thiết cho toàn bộ các bước phân tích tiếp theo (Bước 1, Bước 2, Bước 3,...).

- **Nguồn dữ liệu:**
  - `hr_pipeline_output/clean/combine_clean.csv` (2.019 dòng gốc)
  - `hr_pipeline_output/dashboard/fact_job_skills.csv` (7.783 dòng kỹ năng)
- **Cột khoá nối:** `job_uid`

---

## 2. Quy Trình Xử Lý Chi Tiết

### 2.1. Lọc bỏ tin trùng (Deduplication)
- Giữ các dòng thoả điều kiện: `is_duplicate == False`.
- Kết quả: Giữ lại đúng **1.884** tin tuyển dụng (đã loại bỏ 135 tin trùng lặp giữa các đợt cào hoặc xuất hiện đồng thời trên ITviec và VietnamWorks).

### 2.2. Tính lương trung tâm `salary_mid_m`
- Chỉ tính cho các tin tuyển dụng thoả mãn đồng thời 3 điều kiện:
  1. `salary_type_norm` thuộc nhóm `range` hoặc `exact`.
  2. `salary_needs_review` là `False` (không có dấu hiệu bất thường).
  3. Giá trị lương tính ra lớn hơn 0 (`> 0`).
- Công thức tính:
  - Với tin `range`: $\text{salary\_mid\_m} = \frac{\text{salary\_min\_m} + \text{salary\_max\_m}}{2}$
  - Với tin `exact`: Lấy giá trị của đầu có dữ liệu (`salary_min_m` hoặc `salary_max_m`).
  - Các tin còn lại để trống (`NaN`). Đơn vị tính: triệu VNĐ/tháng.
- Kết quả:
  - Tổng số tin có lương: **422** tin.
  - Trung vị lương ITviec: **42,50** triệu VNĐ.
  - Trung vị lương VietnamWorks: **31,25** triệu VNĐ.

### 2.3. Gắn vai trò và cấp bậc
- Dữ liệu từ `fact_job_skills` được rút gọn về đúng 1 dòng trên mỗi `job_uid` trước khi ghép vào bảng gốc.
- `role_family`: Lấy từ `role_group`. Tin nào thiếu hoặc rỗng được điền `"Other"`.
- `level_final`: Ưu tiên lấy từ `level_norm` nếu khác `"unknown"`. Nếu `level_norm` là `"unknown"`, lấy dự phòng từ `level_dashboard` (nếu khác `"unknown"`). Nếu vẫn không có thì ghi `"unknown"`.
- Kết quả: Còn lại **205** tin có cấp bậc `"unknown"` (số dòng giữ nguyên 1.884 dòng).

### 2.4. Thành phố và loại công ty
- `city_norm`: Lấy từ `city`, các giá trị trống/null được điền `"Khác"`.
- `company_type`: Khởi tạo cột trống (`NaN`), chuẩn bị cho việc gán nhãn ở Bước 1.

### 2.5. Xử lý các cột kỹ năng
- Chỉ lấy các dòng có `valid_job == True` từ `fact_job_skills`.
- **Top 63 kỹ năng:** Kỹ năng xuất hiện trong $\ge 30$ tin tuyển dụng.
  - `sk_<tên_kỹ_năng>`: Biến nhị phân (0 hoặc 1). Xuất hiện nhiều lần trong cùng 1 tin vẫn tính là 1. Tên kỹ năng chuyển thành chữ thường, các ký tự đặc biệt (`khoảng trắng`, `/`, `+`, `#`, `.`) chuyển thành dấu gạch dưới `_`.
  - `w_<tên_kỹ_năng>`: Biến trọng số tương ứng `imp_weight` cao nhất của kỹ năng đó trong tin tuyển dụng:
    - Bắt buộc (`required`): 1.0
    - Ưu tiên (`preferred`): 0.5
    - Mô tả công việc (`duty`): 0.3
    - Chỉ liệt kê (`listed_only`): 0.2
    - Không có: 0.0
- **4 cột tổng hợp (tính trên TẤT CẢ các kỹ năng trong tin):**
  - `n_skills`: Số kỹ năng độc nhất của tin.
  - `n_required`: Số kỹ năng có `importance == 'required'`.
  - `n_advanced`: Số kỹ năng có `proficiency == 'advanced'`.
  - `demand_score`: Tổng `imp_weight` của tất cả các kỹ năng trong tin (mỗi kỹ năng tính 1 lần).

### 2.6. Cấu trúc cột của `analysis_base.csv` (144 cột)
1. **Định danh (4 cột):** `job_uid`, `company_canonical_id`, `company_canonical_name`, `title`
2. **Mô tả tin (9 cột):** `site`, `text_quality`, `posted_date`, `city_norm`, `role_family`, `role_dashboard`, `level_final`, `company_type`, `exp_min_years`
3. **Lương (1 cột):** `salary_mid_m`
4. **Tổng hợp (4 cột):** `n_skills`, `n_required`, `n_advanced`, `demand_score`
5. **Kỹ năng nhị phân (63 cột):** `sk_...`
6. **Kỹ năng trọng số (63 cột):** `w_...`

---

## 3. Bảng Đối Soát Tính Toàn Vẹn (Validation Checklist)

| Chỉ tiêu kiểm tra | Giá trị mong đợi | Giá trị thực tế | Trạng thái |
| :--- | :--- | :--- | :---: |
| Số dòng | 1.884 | **1.884** | **KHỚP** |
| `job_uid` có trùng không | Không trùng (1.884 unique) | **Không trùng** | **KHỚP** |
| Số tin có lương | ~422 | **422** | **KHỚP** |
| Lương trung vị ITviec | ~42,5 triệu | **42,50** triệu | **KHỚP** |
| Lương trung vị VietnamWorks | ~31,25 triệu | **31,25** triệu | **KHỚP** |
| Số công ty có $\ge 5$ tin | 79 | **79** | **KHỚP** |
| Số tin có `posted_date` | 957 (chỉ VNW) | **957** | **KHỚP** |
| Số cột | ~144 cột | **144** | **KHỚP** |
| Cột $sk\_x = 1 \iff w\_x > 0$ | Đúng cho mọi dòng | **Đúng 100% dòng** | **KHỚP** |

---

## 4. Lưu Ý Quan Trọng Cho Các Bước Tiếp Theo
1. **Tránh đa cộng tuyến:** Không đưa đồng thời `sk_x` và `w_x` của cùng một kỹ năng vào cùng một mô hình hồi quy (tương quan tuyến tính gần như tuyệt đối).
2. **Nhóm ẩn danh Navigos:** `company_canonical_id == 'c_navigos_client'` (gồm 53 tin tuyển dụng) là nhóm gộp nhiều client ẩn danh của bên săn đầu người Navigos, không phải một pháp nhân đơn lẻ. Ở Bước 1 và Bước 3 cần loại bỏ hoặc xử lý riêng từng tin.
3. **Tính tái lập:** Toàn bộ quy trình được tự động hoá trong file `phân tích/build_analysis_base.py`. Mọi thay đổi về tham số hoặc ngưỡng trong tương lai cần được sửa trong mã nguồn script để chạy lại từ đầu.
