# Manual Overrides & Curation Repository

Phiên bản: **v1.2 (Snapshot 2026-10-25)**  
Cập nhật lần cuối: **2026-11-23**

## Danh mục tệp ghi đè thủ công
1. `skill_taxonomy.csv`: 72 nhãn kỹ năng chuẩn (canonical skills) tổ chức theo 2 tầng: `skill_family` (Programming Languages, Web & Frontend, Backend & API, AI & Machine Learning, Data Engineering & Analytics, Cloud & DevOps, Infrastructure & System, Quality Assurance & Testing, Architecture & Design, Database, Security, Enterprise Systems, Soft Skills & Management, Human Languages) và `skill_category`.
2. `skill_alias.csv`: 1.696 quy tắc map alias tag kỹ năng vào nhãn chuẩn, hỗ trợ chuỗi gộp (`Java/.Net/Python`), cờ `needs_human_check`, `confidence`, và `match_type`.
3. `salary_review_filled.csv`: 29 bản ghi hiệu chỉnh mức lương bất thường (outlier, placeholder, nhầm currency, gán sàn 'từ').
4. `duplicate_review_filled.csv`: 7 cặp tin tuyển dụng đối soát thủ công (6 duplicate, 1 keep_both).
5. `duplicate_audit_sample_20_filled.csv`: Kết quả đối soát 20 cặp tin trùng tiềm năng (15 duplicate, 4 not_duplicate, 1 uncertain) kèm chỉ số `text_overlap_pct`, `same_exp_or_unknown` và luật bảo vệ chống gộp nhầm (`containment >= 90%` & khớp số năm kinh nghiệm tối thiểu).
