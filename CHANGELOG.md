# Changelog

Tất cả các thay đổi đáng chú ý của dự án **Vietnam IT Job Market & HR Intelligence Pipeline** được ghi lại tại tài liệu này.

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
