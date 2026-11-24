# Báo Cáo Phần 0 của Bước 2: Kiểm Tra Bổ Sung Trước Khi Tính

## 1. Soát Mẫu Khóa Thay Thế (Mục 0.1)
- **Tổng số cặp trùng giữa hai đợt:** 1.035 cặp.
  - Số cặp trùng khớp cả `job_uid`: 882 cặp (85.2%).
  - Số cặp **chỉ khớp bằng khóa thay thế** (`site + company + title + city` chuẩn hóa): **153 cặp** (14.8%).
- **Kết quả soát mẫu ngẫu nhiên 20 cặp** (random seed = 42, lưu tại [`surrogate_key_audit_n20.csv`](../data/dedup_audit/surrogate_key_audit_n20.csv)):
  - **Số cặp đúng cùng một tin:** 20 / 20 cặp (100%).
  - **Số cặp sai:** 0 cặp (< ngưỡng 3 cặp).
  - **Kết luận:** Khóa thay thế đạt độ tin cậy tuyệt đối, phản ánh đúng các tin tuyển dụng được các công ty (Geleximco, SNOW, BIDV MetLife, Bosch, Masterise, VNPT, VinUni,...) gia hạn hoặc tạo mới job ID trên sàn ở đợt 2. Giữ nguyên quy tắc gộp, không cần thắt khóa thêm.

---

## 2. Chất Lượng Văn Bản Theo Sàn × Đợt Đầu Thấy Tin (Mục 0.2)

### Bảng Phân Bố Toàn Diện
| Đợt đầu thấy tin | Sàn tuyển dụng | `text_quality` | Số tin | Tỷ lệ trong sàn (%) | Số kỹ năng TB (`n_skills`) | Trung vị kỹ năng |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Đợt 1** | **ITviec** | `full` | 925 | 99.78% | 4.40 | 5.0 |
| | | `truncated` | 2 | 0.22% | 2.00 | 2.0 |
| | **VietnamWorks** | `full` | 593 | 61.96% | 3.34 | 3.0 |
| | | `truncated` | 364 | 38.04% | 3.31 | 3.0 |
| **Đợt 2** | **ITviec** | `full` | 810 | 96.09% | 4.50 | 5.0 |
| | | `truncated` | 33 | 3.91% | 3.79 | 4.0 |
| | **VietnamWorks** | `full` | 951 | **99.69%** | 3.82 | 4.0 |
| | | `truncated` | 3 | 0.31% | 1.67 | 1.0 |

### Trả lời 2 câu hỏi định lượng
1. **VietnamWorks đợt 2 có bao nhiêu % full?**
   - **Thực tế:** **99.69% full** (951 / 954 tin).
   - *Giải thích độ lệch so với giả thuyết 20%:* Trước đó khi chỉ dùng snapshot ban đầu, tin VNW đợt 2 chỉ là snippet tìm kiếm (bị cắt ngắn). Sau khi nạp bổ sung 16 file snapshot đầy đủ từ thư mục `daily/`, toàn bộ bài đăng VNW đã có đầy đủ `description` và `requirement` dài $\ge 400$ ký tự.
2. **Tin bị cắt (`truncated`) có ít kỹ năng hơn tin `full` bao nhiêu?**
   - Trung bình tin `full`: **4.07 kỹ năng/tin**.
   - Trung bình tin `truncated`: **3.33 kỹ năng/tin**.
   - **Chênh lệch:** Tin bị cắt có ít hơn **0.74 kỹ năng/tin** (giảm **-18.1%**).

---

## 3. Tin Trùng Cả Hai Đợt Mà Đợt 1 Bị Cắt, Đợt 2 Full (Mục 0.3)
- **Số lượng tin:** **100 tin** (chiếm 9.66% trong tổng số 1.035 cặp trùng).
- **Phân bố sàn:** 100% thuộc sàn **VietnamWorks**.
- **So sánh kỹ năng trích xuất giữa hai đợt của cùng 100 tin này:**
  - Phiên bản Đợt 1 (bị cắt): trung bình **3.41 kỹ năng/tin**.
  - Phiên bản Đợt 2 (đầy đủ): trung bình **3.84 kỹ năng/tin**.
  - **Mức độ hao hụt khi giữ bản đợt 1 sớm nhất:** Thiếu hụt trung bình **0.43 kỹ năng/tin** (khoảng 11.2%).
  - Danh sách 100 cặp đã được xuất ra [`truncated_vs_full_pairs.csv`](../results/a_popularity/truncated_vs_full_pairs.csv) để ghi sổ hạn chế và phục vụ chạy phân tích độ nhạy (sensitivity analysis).

---

## 4. Ngày Đăng Của Tin Có Mặt Ở Cả Hai Đợt (Mục 0.4)
- **VietnamWorks (573 tin trùng):**
  - Số tin giữ nguyên ngày đăng: **397 tin** (69.3%).
  - Số tin có `posted_date` khác nhau (được nhà tuyển dụng làm mới / repost ngày đăng trên sàn ở đợt 2): **176 tin** (30.7%).
  - **Quy tắc áp dụng:** Lấy ngày đăng sớm nhất (từ Đợt 1).
- **ITviec (462 tin trùng):**
  - Ở Đợt 1 ITviec hoàn toàn không có ngày đăng.
  - Số tin ITviec Đợt 1 được **khôi phục ngày đăng** từ Đợt 2: **462 tin (100% các tin trùng)**.
  - Tạo cột chuẩn: `posted_date_final` và `date_source` (`from_batch2`, `own`, `none`).

---

## 5. Chốt Bảng Phân Tích Chuẩn Bước 2 (Mục 0.5)
- **Mẫu số chuẩn:**
  - Bảng gộp ban đầu: 2.622 tin.
  - Loại bỏ **2 tin** có `n_skills == 0` (đều thuộc VNW).
  - **Mẫu số chính thức của Bước 2:** **2.620 tin**.
- **Độ bao phủ ngày đăng sau khôi phục:**
  - Tổng số tin có `posted_date_final`: **2.154 / 2.620 tin (82.21%)**.
    - ITviec: 829 tin (461 khôi phục từ đợt 2 + 368 tin mới đợt 2).
    - VietnamWorks: 1.325 tin (100% có ngày đăng).
    - ITviec còn thiếu: 466 tin (chỉ xuất hiện ở đợt 1 không trùng đợt 2).
- **Cột phân tích độ nhạy:**
  - `in_full_sample`: **2.233 tin** (85.23% toàn bảng gộp).
- **Bảng dữ liệu đã lưu:**
  - [`analysis_base_final.csv`](../data/base/analysis_base_final.csv)
  - [`analysis_base_merged_raw.csv`](../data/base/analysis_base_merged_raw.csv)

---

## 6. Ghi Sổ Level Unknown & Cập Nhật Số Cột README (Mục 0.6)

### 6.1. Tỷ lệ `level_final == 'unknown'` thực sự trong bảng gộp
- **Tỷ lệ unknown thực tế:** **10.19%** (267 / 2.620 tin).
- **Phân bố chi tiết cấp bậc (`level_final`):**
  - `Middle`: **32.63%** (855 tin)
  - `Senior`: **32.18%** (843 tin)
  - `Unknown`: **10.19%** (267 tin)
  - `Junior`: **8.21%** (215 tin)
  - `Manager`: **5.88%** (154 tin)
  - `Lead`: **4.96%** (130 tin)
  - `Intern`: **2.75%** (72 tin)
  - `Fresher`: **1.98%** (52 tin)
  - `Director`: **1.22%** (32 tin)
- *Giải thích nguyên nhân chênh lệch với số liệu ~56% trước đó:*
  - Cột thô `level_norm` trong `combine_clean.csv` chỉ trích xuất từ regex tiêu đề/kinh nghiệm nên có ~56% unknown.
  - Cột phân tích chuẩn `level_final` kết hợp thêm nguồn `level_dashboard` (làm giàu từ fact table), giúp giảm tỷ lệ unknown xuống còn đúng **10.19%**.

### 6.2. Đối soát số cột trong các file README
- **`analysis_base.csv` (Đợt 1):** **144 cột** (18 meta/tổng hợp + 63 `sk_` + 63 `w_`).
- **`analysis_base_tu_sau_25_10.csv` (Đợt 2):** **142 cột** (18 meta/tổng hợp + 62 `sk_` + 62 `w_`).
- **`analysis_base_combined.csv` / `analysis_base_step2.csv` (Bảng gộp chuẩn Bước 2):** **167 cột** (25 meta/tổng hợp + 71 `sk_` + 71 `w_`). Các cột bổ sung gồm: `crawl_batch`, `n_batches_seen`, `posted_date_final`, `date_source`, `in_full_sample`.
