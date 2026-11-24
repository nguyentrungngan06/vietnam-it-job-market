# Changelog

Tất cả các thay đổi đáng chú ý của dự án **Vietnam IT Job Market & HR Intelligence Pipeline** được ghi lại tại tài liệu này.

## [1.1.0] - 2026-11-25

### Tích Hợp Module Phân Tích Chuyên Sâu Kỹ Năng (`01_eda_skill_analysis/`)
- **Mở rộng phạm vi dữ liệu quan sát**:
  - Gộp thành công 2 đợt cào (10/10 – giữa tháng 11/2026) với 3.655 lượt quan sát $\rightarrow$ **2.620 tin tuyển dụng độc nhất**.
  - Áp dụng khóa thay thế liên đợt (`site + company + title + city`), kiểm toán mẫu ngẫu nhiên 40 cặp đạt độ chính xác **100% (40/40)**.
  - Khôi phục thành công ngày đăng cho **461 tin độc nhất** của ITviec Đợt 1 từ Đợt 2, thiết lập chuỗi quan sát tuần trên cả hai nền tảng.
  - Bổ sung dữ liệu văn bản từ snapshot `daily/`, đưa tỷ lệ tin đầy đủ (`text_quality == 'full'`) của VietnamWorks Đợt 2 lên **99.69%**.

### Kết Quả Nghiên Cứu Định Lượng & Khắc Phục Phương Pháp Luận
- **Phần A (Popularity & Nhóm bậc)**:
  - Phân nhóm Top kỹ năng theo 2 bậc: Tier 1 (Top 5: $\ge 10.5\%$, dẫn đầu bởi English, Python, AI, SQL, Architecture) và Tier 2 (10 kỹ năng: 8.5% – 10.1%).
  - Bổ sung khoảng tin cậy Cluster Bootstrap 95% qua 500 vòng lặp theo công ty, mở rộng biên độ sai số từ +1.5% đến +77.0% so với giả định độc lập.
- **Phần B (Xu hướng thời gian & Kiểm soát nguồn)**:
  - Lập bảng chéo phát hiện ranh giới bước nhảy nguồn ngày 26/10.
  - Giải mã nghịch lý 70% độ dốc âm bằng phân tích số kỹ năng TB và kiểm tra đối chứng tại ITviec (53.7% âm vs 46.3% dương), bác bỏ giả thuyết nguồn làm tăng đồng loạt.
  - Diễn giải đúng bản chất công suất kiểm định thấp ($q_{\text{FDR}} \ge 0.09$) và phân loại chuỗi tuần là phân tích mô tả quan sát.
- **Phần C (Đồng xuất hiện & FP-Growth)**:
  - Đo lường tỷ lệ chứa nhau hai chiều, phát hiện và gắn cờ [CHỒNG CHÉO ĐỊNH NGHĨA] cho cặp `JS/TS` $\leftrightarrow$ `Angular` (97.2%).
  - Tách bạch cặp cùng hệ sinh thái phân cấp (`Java` $\leftrightarrow$ `Spring`: 87.5%) và cặp liên họ công nghệ độc lập (`Node.js` $\leftrightarrow$ `React`, `Python` $\leftrightarrow$ `AI`, `SQL` $\leftrightarrow$ `Python`).
  - Xuất bản danh sách 55 cặp kỹ năng bền vững qua kiểm chứng chéo.
- **Phần D (Mạng lưới & Phân cụm Louvain)**:
  - Xây dựng đồ thị mạng lưới 71 nút kỹ năng, 10 cộng đồng công nghệ và 16 nút kỹ năng độc lập.
  - Tính toán Adjusted Rand Index (ARI) trên tập nút giao nhau: ARI = 0.82 (ổn định tham số), ARI = 0.65 (chia đôi theo công ty), ARI = 0.27 (khác biệt sàn tổng hòa từ 3 nguyên nhân).

### Chuẩn Hóa Kiến Trúc Dự Án
- Tái cấu trúc thư mục phân tích thành `01_eda_skill_analysis/` gồm 4 nhánh chuẩn: `reports/`, `code/`, `data/` (base, dedup_audit, reference), `results/` (a_popularity, b_trends, c_cooccurrence, d_network).
- Bảo toàn 100% lịch sử Git thông qua `git mv`, chuyển đổi toàn bộ liên kết sang định dạng markdown tương đối của GitHub.

## [1.0.0] - 2026-11-23

### Kiến Trúc & Cấu Trúc Mã Nguồn
- **Tách bạch 2 phân hệ độc lập**:
  - `crawlers/`: Module thu thập dữ liệu đa nguồn (ITviec, VietnamWorks, GitHub) kèm tài liệu hướng dẫn vận hành riêng tại `crawlers/README.md`.
  - `pipeline/`: Hệ thống Data Pipeline làm sạch, chuẩn hóa, gán nhãn kỹ năng 2 tầng, khử trùng lặp và dựng mô hình Star Schema, kèm tài liệu kỹ thuật tại `pipeline/README.md`.
  - Root `README.md`: Báo cáo tổng hợp luồng dữ liệu end-to-end từ thu thập tới phân tích thị trường.

### Chuẩn Hóa Dữ Liệu & Số Liệu Kiểm Định Thực Tế (Snapshot 10/10 - 25/10/2026)
- **Từ điển Kỹ năng 2 tầng (Taxonomy)**:
  - 99 nhãn kỹ năng chuẩn hóa thuộc các nhóm `skill_family` và `skill_category`.
  - 1.696 quy tắc map alias trong `skill_alias.csv`, phân tách các chuỗi ghép phức hợp (ví dụ: `CI/CD`, `C/C++` được bảo vệ; `Java/.Net` được tách thành các kỹ năng độc lập).
- **Cấp bậc suy luận (Level Inference)**:
  - Tỷ lệ cấp bậc chưa xác định (`unknown`) giảm từ 57% xuống còn **11.69%** (236/2.019 tin, đạt mục tiêu < 12%) nhờ ưu tiên nhận diện từ khóa chức danh và suy luận bổ trợ qua số năm kinh nghiệm yêu cầu.
- **Phân loại vai trò kỹ thuật (Role Rules)**:
  - Bổ sung hệ luật regex nhận diện 20 nhóm vai trò công nghệ chuyên sâu (AI/ML, Data Engineer, Cloud, DevOps, Embedded, Security, Fullstack...).
  - Tỷ lệ tin rơi vào nhóm `other` giảm từ 40% xuống còn **26.80%** (541/2.019 tin).
- **Chuẩn hóa nhóm vị trí (Role Group Classification)**:
  - Phân loại 15 nhóm vị trí chuẩn (`role_group`): Backend, Frontend, Fullstack, Mobile, Data / AI, DevOps / Cloud / SysAdmin, QA / QC / Tester, BA / PO / PM, Security, IT Support / ERP, Management / Leadership, UI / UX Design, Embedded / Hardware / Telecom, Game Dev, Other.
  - Phân bổ thực tế trên 1.884 tin hợp lệ: ITviec = 927 tin (49.20%), VietnamWorks = 957 tin (50.80%).
  - Kiểm soát ranh giới nghiêm ngặt cho Data / AI (286 tin - 15.18%) và Management / Leadership (23 tin - 1.22%).
  - Bổ sung `role_source` (72.35% title, 5.94% job_function, 1.01% skills, 20.70% unknown) và `role_confidence` (69.32% high, 6.95% medium, 23.73% low).
  - Kiểm toán mẫu ngẫu nhiên 100 tin (`seed=42`) đạt độ chính xác **96.0%**.
- **Chuẩn mực mức lương (`salary_benchmarks.csv`)**:
  - Tách bạch 3 nhóm dữ liệu lương: Khoảng lương (`range`), mức sàn ("Từ X" - `from`), và mức trần quảng cáo ("Tới X" - `up_to`).
  - Đạt chính xác **27 / 96 ô** phân khúc vai trò - cấp bậc có cỡ mẫu tin cậy $n_{\text{range}} \ge 5$.
  - Triệt tiêu hiển thị (gán về `NaN`) cho các ô $n < 5$ nhằm tránh hiện tượng $p25 = p75 = \text{median}$ trên cỡ mẫu nhỏ.
- **Chất lượng mô tả JD**:
  - **1.583 / 2.019 tin (78.4%)** đạt chất lượng văn bản đầy đủ (`text_quality == 'full'`), bao gồm 968 tin ITviec và 618 tin VietnamWorks được làm giàu chi tiết.
- **Khử trùng lặp có luật bảo vệ (Guard Rule Deduplication)**:
  - Áp dụng điều kiện ngặt: $\text{text\_containment} \ge 90\%$ và số năm kinh nghiệm tương thích.
  - Loại bỏ hoàn toàn nguy cơ nối chuỗi bắc cầu (Transitive Chaining) bằng cơ chế kiểm tra chéo trực tiếp với Primary Job.
  - **Kiểm định độc lập**: Kiểm toán thêm 30 cặp tin mới được gộp tự động (`duplicate_validation_sample_30.csv`), ghi nhận độ chính xác **30/30 (100%)** là các tin đăng trùng thực tế.

### Tuân Thủ Pháp Lý & An Toàn Dữ Liệu
- Toàn bộ dữ liệu công bố tại kho lưu trữ là metadata đã chuẩn hóa (chức danh, công ty, thành phố, khoảng lương, cấp bậc, nhãn kỹ năng).
- Không lưu trữ và không phân phối văn bản mô tả tuyển dụng đầy đủ (Full JD Description/Requirement) để bảo vệ bản quyền nội dung của nhà tuyển dụng và các nền tảng tuyển dụng.
- Cung cấp bộ dữ liệu mẫu 50 dòng (`data/sample/`) phục vụ mục đích kiểm thử và tái hiện pipeline.
