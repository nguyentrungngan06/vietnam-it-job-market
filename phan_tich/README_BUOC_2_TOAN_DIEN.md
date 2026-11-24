# Báo Cáo Toàn Diện Bước 2: Phân Tích Chuyên Sâu Kỹ Năng IT Việt Nam (Phiên Bản Hoàn Thiện)

Báo cáo này tổng hợp toàn bộ kết quả phân tích Bước 2 trên bộ dữ liệu chuẩn hóa **2.620 tin tuyển dụng** (sau khi loại 2 tin có $n\_skills = 0$), bao gồm các phép kiểm tra tiền kỳ (0.1–0.10) và 4 phần phân tích chuyên sâu (Phần A, B, C, D) đã được hoàn thiện với diễn giải phương pháp luận cẩn trọng.

---

## 1. Nghiệm Thu Các Điểm Kiểm Tra Bổ Sung (0.1 – 0.10)

| Mục kiểm tra | Kết quả thực tế & Đo lường định lượng | Kết luận & Quy tắc áp dụng |
| :--- | :--- | :--- |
| **0.1 & 0.8. Soát mẫu khóa thay thế** | Soát đúng mẫu **40 cặp ngẫu nhiên** từ 153 cặp chỉ khớp bằng khóa thay thế (`site + company + title + city`): **40/40 cặp đúng cùng một tin tuyển dụng (100% khớp, 0 cặp sai)**. | Khóa thay thế đạt độ tin cậy thực nghiệm rất cao. Giữ nguyên quy tắc gộp, không cần thắt khóa thêm. |
| **0.7. Khớp một - nhiều** | Có **5 tin Đợt 1** và **6 tin Đợt 2** tham gia vào các liên kết một-nhiều (18 cặp trong [`one_to_many_duplicate_matches.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/one_to_many_duplicate_matches.csv)).<br>• *Ví dụ 1:* Ban Viên Corp tuyển thêm 1 Senior .NET mới sau 1 tháng.<br>• *Ví dụ 2:* Public Bank tuyển thêm 1 IT Audit Junior (2 năm kn) bên cạnh vị trí Senior (6 năm kn).<br>• *Ví dụ 3:* ITviec lệch 461 vs 462 do đúng 1 tin Đợt 1 (`itviec:4996245219`) khớp với 2 tin Đợt 2. | Số lượng tin bị gộp nhầm tối đa chỉ khoảng **5–6 tin** (chiếm ~0.2% mẫu), hoàn toàn không làm sai lệch phân tích tổng thể. |
| **0.2. Chất lượng văn bản theo sàn** | • **VietnamWorks Đợt 2:** đạt **99.69% full** (951/954 tin) nhờ bổ sung 16 snapshot đầy đủ từ `daily/`.<br>• **Số kỹ năng TB:** Tin `full` = 4.07 skills/tin; Tin `truncated` = 3.33 skills/tin (ít hơn 0.74 kỹ năng, -18.1%).<br>• *Hiệu ứng sàn:* VNW Đợt 1 full đạt 3.34 so với truncated 3.31 (chênh lệch rất nhỏ trong nội bộ sàn). | Xác nhận VNW đợt 2 không bị cắt cụt. Bảng phân bố đã sửa nhãn tổng tin chuẩn theo từng đợt. |
| **0.3. Đợt 1 cắt, Đợt 2 full** | Có **100 tin** (100% VNW) ở Đợt 1 bị cắt nhưng Đợt 2 là full. Kỹ năng TB tăng từ 3.41 lên 3.84 (+0.43 skills/tin). Đã lưu tại [`batch1_truncated_batch2_full_pairs.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/batch1_truncated_batch2_full_pairs.csv). | Đưa vào phân tích độ nhạy (Bản 2 ở Phần A) để kiểm chứng tính vững chắc. |
| **0.4. Khôi phục ngày đăng ITviec** | • VNW: 176 tin (30.7%) được repost/làm mới ngày đăng ở Đợt 2 $\rightarrow$ Lấy ngày sớm nhất từ Đợt 1.<br>• ITviec: Khôi phục thành công ngày đăng cho **461 tin độc nhất** từ Đợt 2. | Tạo cột chuẩn `posted_date_final` và `date_source` (`from_batch2`: 461, `own`: 1.693, `none`: 466). |
| **0.9. Kiểm tra bảng gộp sau nạp lại** | • Tin mới VNW Đợt 2 có số kỹ năng TB: **3.75 skills/tin**, tỷ lệ full: **99.46%**.<br>• Số kỹ năng $\ge 30$ tin: **71 kỹ năng** (giữ nguyên). | Bảng cơ sở gộp 2.620 tin kế thừa đầy đủ 71 cột nhị phân `sk_` và 71 cột trọng số `w_`. |
| **0.10. Độ ổn định trích xuất** | Trên 922 cặp tin trùng mà cả 2 bản đều full:<br>• **ITviec (N=450):** Đợt 1 = 4.427 vs Đợt 2 = 4.509 (chênh lệch +0.082 skills, +1.86% $\rightarrow$ **Cực kỳ ổn định**).<br>• **VietnamWorks (N=472):** Đợt 1 = 3.364 vs Đợt 2 = 3.845 (+0.481 skills, +14.29%). | Do JD Đợt 2 của VNW từ `daily/` dài và chi tiết hơn, bóc được thêm kỹ năng phụ $\rightarrow$ Cần kiểm soát biến `crawl_batch` trong Phần B. |

---

## 2. Phần A: Xếp Hạng Kỹ Năng Phổ Biến Theo Nhóm Bậc (Tiers)

Thay vì diễn giải thứ hạng đơn lẻ dễ gây ngộ nhận (do sai số phân cụm theo công ty), danh mục kỹ năng được phân chia thành **2 nhóm bậc nhu cầu chính**:

### Bậc 1 (Tier 1 - Nhu Cầu Vượt Trội): Top 5 Kỹ Năng ($\ge 10.5\%$)
Nhóm này có khoảng cách phân tách rõ rệt với phần còn lại của thị trường và **giữ nguyên tuyệt đối vị trí thứ hạng qua cả 3 bản phân tích độ nhạy**:
1. **English (16.37%, 429 tin):** Kỹ năng nền tảng hàng đầu, đặc biệt vượt trội tại ITviec (26.49%) so với VNW (6.49%). Khoảng tin cậy Bootstrap cụm mở rộng lên $[14.11\%, 19.12\%]$ (+77.0%) do các công ty FDI/outsourcing đăng tuyển hàng loạt.
2. **Python (15.80%, 414 tin):** Ngôn ngữ phổ biến nhất, là cầu nối giữa Data, AI và Backend.
3. **Artificial Intelligence - AI (14.24%, 373 tin):** Nhu cầu tăng trưởng mạnh mẽ, xuất hiện ở 19.31% tin ITviec.
4. **SQL (14.08%, 369 tin):** Kỹ năng dữ liệu cốt lõi bắt buộc ở hầu hết các vai trò Backend, Data và Phân tích.
5. **Software Architecture & Design (10.57%, 277 tin):** Tiêu chuẩn thiết kế hệ thống quan trọng trong các JD Senior/Lead.

### Bậc 2 (Tier 2 - Nhóm Bám Đuổi Sít Sao): 10 Kỹ Năng (8.5% – 10.1%)
Các kỹ năng trong nhóm này có tỷ lệ tuyển dụng chênh lệch nhau chỉ từ 0.1% – 0.5% (hoàn toàn nằm trong biên độ sai số Bootstrap $[7.5\%, 11.3\%]$) nên được xem là có mức độ phổ biến tương đương nhau:
- **Business Analysis (BA)** (10.08%, 264 tin)
- **Project Management** (9.54%, 250 tin)
- **.NET / C#** (9.50%, 249 tin)
- **Cybersecurity** (9.43%, 247 tin)
- **Java** (9.24%, 242 tin)
- **Digital Transformation / IT Consulting** (9.24%, 242 tin)
- **ERP / CRM / Enterprise Apps** (9.20%, 241 tin)
- **Agile & Scrum** (9.01%, 236 tin)
- **Data Analysis** (8.82%, 231 tin)
- **Software Engineering general** (8.59%, 225 tin)

> [!NOTE]
> **Ghi chú về sự khác biệt giữa hai sàn:**
> Sự chênh lệch tỷ lệ kỹ năng giữa hai sàn (ví dụ English 26.5% ở ITviec vs 6.5% ở VNW; Software Engineering general 4.4% ở ITviec vs 12.7% ở VNW) phản ánh **phương thức trích xuất dữ liệu** (ITviec tick chọn thẻ tag định sẵn vs VNW trích xuất từ văn bản tự do). Nhận định "ITviec chuyên sâu Web/Cloud, VNW thiên về CNTT doanh nghiệp, ERP, tư vấn" được giữ nguyên dưới dạng **giả thuyết mô tả**, không đồng nhất thành kết luận bản chất thị trường.

---

## 3. Phần B: Kỹ Năng Thay Đổi Theo Thời Gian (Kiểm Soát Nguồn & Confounding)

Đã xuất bản:
- [`skill_trend_weekly.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/skill_trend_weekly.csv) (Chuỗi tuần).
- [`skill_trend_summary.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/skill_trend_summary.csv) (Hồi quy Logistic kèm Cluster SE).
- [`skill_trend_sensitivity_and_confounding.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/skill_trend_sensitivity_and_confounding.csv).

### 3.1. Bảng Chéo Tuần × Đợt Cào (`crawl_batch`) Của VietnamWorks
Bảng chéo dưới đây xác nhận hiện tượng **phân tách ranh giới sạch** giữa hai đợt cào:

| Tuần bắt đầu (`week_start`) | Đợt 1 (`crawl_batch=1`) | Đợt 2 (`crawl_batch=2`) | Tổng tin | % Đợt 1 | % Đợt 2 | Phân loại giai đoạn |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **2026-09-07** | 43 | 0 | 43 | 100.0% | 0.0% | Tuần biên sớm (đã loại) |
| **2026-09-14** | 115 | 0 | 115 | 100.0% | 0.0% | 100% Đợt 1 |
| **2026-09-21** | 124 | 0 | 124 | 100.0% | 0.0% | 100% Đợt 1 |
| **2026-09-28** | 171 | 0 | 171 | 100.0% | 0.0% | 100% Đợt 1 |
| **2026-10-05** | 173 | 1 | 174 | 99.4% | 0.6% | **Đợt 1 ($\ge 99\%$)** |
| **2026-10-12** | 151 | 0 | 151 | 100.0% | 0.0% | **Đợt 1 ($\ge 99\%$)** |
| **2026-10-19** | 178 | 1 | 179 | 99.4% | 0.6% | **Đợt 1 ($\ge 99\%$)** |
| **2026-10-26** | 0 | 102 | 102 | **0.0%** | **100.0%** | **Ranh giới bước nhảy sạch (100% Đợt 2)** |
| **2026-11-02** | 0 | 108 | 108 | 0.0% | 100.0% | 100% Đợt 2 |
| **2026-11-09** | 0 | 77 | 77 | 0.0% | 100.0% | 100% Đợt 2 |
| **2026-11-16** | 0 | 81 | 81 | 0.0% | 100.0% | Tuần biên muộn (đã loại) |

### 3.2. Ba Phép Kiểm Tra Rẻ Làm Rõ Nghịch Lý Độ Dốc Âm
Có một điểm đáng chú ý: Dù Đợt 2 VNW có số kỹ năng TB cao hơn (3.75 vs 3.34), nhưng khi hồi quy theo tuần, **70% kỹ năng lại có độ dốc âm**. Ba phép kiểm tra thực nghiệm đã làm sáng tỏ cơ chế này:
1. **Số kỹ năng TB theo tuần của VNW (`avg_skills`):** Tuần 14/09 là 3.37, tăng lên đỉnh **3.80 – 3.85 vào các tuần 05/10 và 12/10** (cuối Đợt 1), sau đó ở Đợt 2 (sau 26/10) duy trì ở mức **3.63 – 3.71**, đến tuần 09/11 là 3.93. Nghĩa là số kỹ năng TB thực chất đã đạt đỉnh ở giữa chuỗi chứ không phải tăng liên tục từ đầu đến cuối.
2. **Kiểm tra chéo tại sàn ITviec (hầu như không đổi nguồn):** Tỷ lệ độ dốc phân bố rất cân bằng: **53.7% âm ($\beta < 0$) vs 46.3% dương ($\beta > 0$)**.
3. **Kiểm soát thêm biến vai trò (`role_family`):** Có tới **75.0% độ dốc âm nhẹ**, chứng minh cơ cấu tuyển dụng nửa cuối tháng 10 ở VNW có sự gia tăng của các nhóm vai trò có yêu cầu kỹ năng phân tán hơn, làm loãng tỷ lệ xuất hiện của các kỹ năng đơn lẻ phổ biến.
$\implies$ **Kết luận:** Kết quả thực nghiệm **không ủng hộ giả thuyết nhiễu nguồn làm tăng đồng loạt mọi kỹ năng**.

### 3.3. Diễn Giải Đúng Đắn: Công Suất Kiểm Định Thấp (Inconclusive)
Sau hiệu chỉnh Benjamini-Hochberg (FDR), toàn bộ các kỹ năng đều có $q_{\text{FDR}} \ge 0.09$ (không có ý nghĩa thống kê).
> [!WARNING]
> Không kết luận rằng "thị trường chắc chắn ổn định". Việc không phát hiện ý nghĩa thống kê phản ánh **công suất thống kê thấp (low statistical power)**: chuỗi chỉ 9 tuần ở VNW (6 tuần ở ITviec), có khoảng trống 10 ngày và thiên lệch sống sót. Khoảng tin cậy của độ dốc khá rộng (ví dụ Python: $[-0.18, -0.02]$, OR tuần: $[0.84, 0.98]$).
> Kết luận chính xác là: **Dữ liệu chưa đủ bằng chứng để khẳng định có xu hướng tăng hay giảm thực sự**. Mọi phân tích chuỗi tuần chỉ mang tính chất **mô tả quan sát (descriptive)**.

---

## 4. Phần C: Cặp Kỹ Năng Đi Cùng Nhau & Loại Bỏ Chồng Chéo Định Nghĩa

Đã xuất bản:
- [`skill_pairs_npmi.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/skill_pairs_npmi.csv) (1.501 dòng cặp kỹ năng).
- [`skill_inclusion_and_taxonomy_overlap.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/skill_inclusion_and_taxonomy_overlap.csv) (Đo tỷ lệ chứa nhau giữa các kỹ năng gần nghĩa).
- [`skill_pairs_robust_cross_validation.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/skill_pairs_robust_cross_validation.csv) (55 cặp giữ vững qua các bản kiểm tra).

### 4.1. Đo Tỷ Lệ Chứa Nhau & Gắn Nhãn Chồng Chéo Định Nghĩa (Taxonomy Overlap)
Đã tính toán tỷ lệ bao hàm hai chiều $P(A \mid B)$ và $P(B \mid A)$ giữa các kỹ năng gần nghĩa:
- **`JavaScript / TypeScript` $\leftrightarrow$ `Angular`:** Tỷ lệ chứa nhau đạt **97.2%** ($P(\text{JS/TS} \mid \text{Angular}) = 97.2\%$). Hầu hết các tin tuyển Angular trên sàn ITviec đều tự động đi kèm thẻ tag JavaScript/TypeScript $\implies$ **Gắn nhãn [CHỒNG CHÉO ĐỊNH NGHĨA]**, loại khỏi danh sách phát hiện thực sự.
- **`Java` $\leftrightarrow$ `Spring / Java frameworks`:** Tỷ lệ chứa nhau đạt **87.5%** ($P(\text{Java} \mid \text{Spring}) = 87.5\%$). Khi yêu cầu Spring thì 87.5% JD ghi kèm từ khóa Java $\implies$ **Cặp cùng hệ sinh thái phân cấp (Hierarchical Tech Ecosystem)**.

### 4.2. Phân Tách Hai Nhóm Cặp Kỹ Năng Thực Sự Độc Lập

#### Nhóm 1: Cặp Cùng Hệ Sinh Thái Công Nghệ (Intra-family / Tech Stack)
Đại diện cho chuyên môn hóa sâu trong từng mảng kỹ thuật:
1. `Software Testing` $\leftrightarrow$ `Test Automation` (Testing/QA, NPMI = 0.592, Max Inclusion = 58.9%)
2. `QA/QC` $\leftrightarrow$ `Test Automation` (Testing/QA, NPMI = 0.560, Max Inclusion = 43.5%)
3. `DevOps` $\leftrightarrow$ `Kubernetes` (DevOps/Cloud, NPMI = 0.551, Max Inclusion = 51.2%)
4. `Data Visualization / BI` $\leftrightarrow$ `Power BI` (BI/Analytics, NPMI = 0.520, Max Inclusion = 34.6%)
5. `Docker` $\leftrightarrow$ `Kubernetes` (DevOps/Cloud, NPMI = 0.520, Max Inclusion = 34.1%)
6. `Microservices` $\leftrightarrow$ `Software Architecture` (Architecture, NPMI = 0.517)

#### Nhóm 2: Cặp Liên Họ Công Nghệ Thực Sự (Cross-Family) — *Đáng chú ý cho Bước 7 Gợi ý kỹ năng*
Đại diện cho sự kết hợp đa kỹ năng độc lập (cross-functional stacks):
1. **`Node.js` (Backend) $\leftrightarrow$ `React` (Frontend):** NPMI = **0.606** (n=33, Max Inclusion = 50.8%) — *Fullstack JavaScript*
2. **`React` (Frontend) $\leftrightarrow$ `TypeScript` (Lang):** NPMI = **0.562** (n=36, Max Inclusion = 33.8%)
3. **`C/C++` (Lang) $\leftrightarrow$ `Embedded & Firmware` (Embedded):** NPMI = **0.607** (n=45, Max Inclusion = 46.9%)
4. **`HTML / CSS` (Frontend) $\leftrightarrow$ `JavaScript` (Lang):** NPMI = **0.587** (n=30, Max Inclusion = 60.0%)
5. **`Python` (Lang) $\leftrightarrow$ `Artificial Intelligence (AI)` (AI/ML):** Lift = **2.09**, Conf = **29.71%**, Max Inclusion = 33.0%
6. **`SQL` (Database) $\leftrightarrow$ `Python` (Lang):** Lift = **2.06**, Conf = **32.52%**, Max Inclusion = 32.5%
7. **`Linux` (DevOps/OS) $\leftrightarrow$ `Virtualization` (Infra Support):** NPMI = **0.496** (n=20)
8. **`MySQL` (Database) $\leftrightarrow$ `PHP` (Lang):** NPMI = **0.497** ($n=13$ $\rightarrow$ *Ghi chú rõ: Đây là cặp biên do cỡ mẫu thấp*).

---

## 5. Phần D: Mạng Lưới, Nút Cô Lập & Hiệu Chỉnh Diễn Giải ARI

Đã xuất bản:
- [`network_nodes.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/network_nodes.csv) (71 nút kỹ năng).
- [`network_edges.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/network_edges.csv) (75 cạnh liên kết mạnh $\text{NPMI} \ge 0.3$, $n_{ij} \ge 10$).
- [`network_community_robustness_ari.csv`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/network_community_robustness_ari.csv) (Đánh giá ARI).
- [`network_graph.svg`](file:///c:/Users/ADMIN/Downloads/hr_market_dashboard_pipeline/phân%20tích/network_graph.svg) (Đồ thị vector).

### 5.1. Danh Sách 16 Kỹ Năng Cô Lập (Không Đủ Liên Kết NPMI $\ge 0.3$)
Trong 67 kỹ năng chính, có **51 kỹ năng** nằm trong 10 cụm đa nút và **16 kỹ năng đứng độc lập** (không có cạnh nào đạt ngưỡng kết nối):
- `Business Analysis (BA)` (264 tin, 10.1%)
- `.NET / C#` (249 tin, 9.5%)
- `Cybersecurity` (247 tin, 9.4%)
- `Digital Transformation / IT Consulting` (242 tin, 9.2%)
- `ERP / CRM / Enterprise Apps` (241 tin, 9.2%)
- `Software Engineering (general)` (225 tin, 8.6%)
- `API Development` (211 tin, 8.1%)
- `Communication & Teamwork` (165 tin, 6.3%)
- `UI/UX Design` (141 tin, 5.4%)
- `Product Management` (135 tin, 5.2%)
- `Leadership & People Management` (128 tin, 4.9%)
- `Data Governance & Management` (83 tin, 3.2%)
- `Mobile Development` (60 tin, 2.3%)
- `Blockchain / Fintech` (50 tin, 1.9%)
- `Version Control (Git)` (40 tin, 1.5%)
- `Automation & RPA` (31 tin, 1.2%)

### 5.2. Chuẩn Hóa Tên 10 Cụm Kỹ Năng
- Cụm 1: **Cloud Computing & DevOps** (8 kỹ năng)
- Cụm 2: **Cơ sở dữ liệu & Ngôn ngữ Backend** (Go, PHP, MySQL, Postgres, Oracle, MongoDB) (8 kỹ năng)
- Cụm 3: **Modern Web & Frontend** (8 kỹ năng: JS, TS, React, Node.js, Angular, HTML/CSS, Full Stack, JS/TS)
- Cụm 4: **Hạ tầng CNTT & Quản trị hệ thống** (5 kỹ năng)
- Cụm 5: **Enterprise Java & Kiến trúc phần mềm** (4 kỹ năng)
- Cụm 6: **Phân tích dữ liệu & BI** (4 kỹ năng)
- Cụm 7: **Trí tuệ nhân tạo & Khoa học dữ liệu** (3 kỹ năng)
- Cụm 8: **Kiểm thử & Đảm bảo chất lượng** (3 kỹ năng)
- Cụm 9: **Hệ thống nhúng & IoT** (2 kỹ năng)
- Cụm 10: **Kỹ thuật dữ liệu lớn & Kho dữ liệu** (2 kỹ năng)

### 5.3. Diễn Giải Đúng Mực Về Chỉ Số Adjusted Rand Index (ARI)
- **Phương pháp tính:** Tính toán chặt chẽ trên **tập nút giao nhau (common nodes)** giữa 2 phân hoạch.
- **ARI = 0.8205 (ngưỡng 0.3 vs 0.4):** Chỉ cho thấy cấu trúc cụm không nhạy cảm với việc thay đổi ngưỡng cạnh trên cùng một bộ dữ liệu (đây là kiểm tra độ ổn định tham số, không phải kiểm định độc lập).
- **ARI = 0.6524 (chia đôi ngẫu nhiên theo công ty):** Cấu trúc phân cụ **khá ổn định**, không bị chi phối cục bộ bởi một vài công ty lớn.
- **ARI = 0.2736 (giữa mạng ITviec và VietnamWorks):** Cộng đồng kỹ năng **chỉ tái lập một phần** giữa hai sàn. Kết quả này phản ánh sự tổng hòa của **3 nguyên nhân chưa tách rời được**:
  1. Cơ cấu phân khúc thị trường của 2 sàn khác nhau.
  2. Phương thức trích xuất kỹ năng khác nhau (tag định sẵn vs regex tự do).
  3. Mỗi sàn chỉ sử dụng một nửa dung lượng mẫu, làm giảm mật độ cạnh kết nối.

---

## 6. Bổ Sung Mục Hạn Chế Phương Pháp Luận
1. **Thiên lệch sống sót ở phân tích phụ:** Phân tích phụ trên tập tin trùng (cố định nguồn văn bản đợt 2) toàn bộ là các tin còn tồn tại đến đợt 2, nên cũng chịu thiên lệch sống sót tương tự chuỗi ITviec.
2. **Chia sẻ dữ liệu giữa hai đợt cào:** Khoảng 56.3% – 58.9% tin trùng nhau; bảng gộp giữ lần quan sát sớm nhất để loại trùng.
3. **Chuỗi thời gian ngắn & khoảng trống 10 ngày:** Chuỗi 6–9 tuần với khoảng trống từ 25/10 đến 04/11 khiến các phân tích xu hướng chỉ mang tính mô tả quan sát.
