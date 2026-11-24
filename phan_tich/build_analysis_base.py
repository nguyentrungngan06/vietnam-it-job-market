"""
Xây dựng bảng phân tích cơ sở analysis_base.csv (Bước 0)

Mục tiêu:
- Đọc combine_clean.csv và fact_job_skills.csv
- Lọc bỏ tin trùng (is_duplicate == False) -> 1.884 tin
- Tính lương trung tâm salary_mid_m cho tin hợp lệ (> 0, exact hoặc range, không needs_review)
- Rút gọn và nối vai trò (role_family, role_dashboard) và cấp bậc (level_final)
- Chuẩn hoá thành phố (city_norm) và cột rỗng company_type
- Tạo 63 cột kỹ năng nhị phân sk_... và 63 cột trọng số w_... (kỹ năng xuất hiện >= 30 tin)
- Tạo 4 cột tổng hợp: n_skills, n_required, n_advanced, demand_score
- Xuất ra file analysis_base.csv (UTF-8 with BOM: utf-8-sig)
"""

import os
import sys
import pandas as pd
import numpy as np


def clean_skill_col_name(skill_name: str) -> str:
    """
    Đặt tên cột kỹ năng:
    - Chữ thường (lower)
    - Ký tự đặc biệt (khoảng trắng, /, +, #, .) đổi thành dấu gạch dưới '_'
    Ví dụ: 'C++' -> 'c__'
           '.NET / C#' -> '_net___c_'
    """
    cleaned = skill_name.lower()
    for ch in [' ', '/', '+', '#', '.']:
        cleaned = cleaned.replace(ch, '_')
    return cleaned


def calculate_salary_mid(row) -> float:
    """
    Chỉ tính cho tin thoả cả 3 điều kiện:
    1. salary_type_norm là 'range' hoặc 'exact'
    2. salary_needs_review là False
    3. Lương tính ra > 0
    Với 'range': trung bình cộng salary_min_m và salary_max_m
    Với 'exact': lấy giá trị của đầu có dữ liệu
    Các tin còn lại để NaN
    """
    st = row.get('salary_type_norm')
    snr = row.get('salary_needs_review')
    if snr is True or st not in ['range', 'exact']:
        return np.nan

    smin = row.get('salary_min_m')
    smax = row.get('salary_max_m')

    if st == 'range':
        val = (smin + smax) / 2.0
    elif st == 'exact':
        val = smin if pd.notna(smin) and smin > 0 else smax
    else:
        val = np.nan

    return val if pd.notna(val) and val > 0 else np.nan


def determine_final_level(row) -> str:
    """
    level_final:
    - Nếu level_norm khác 'unknown' (và không rỗng) -> dùng level_norm
    - Nếu là 'unknown' -> dùng level_dashboard (nếu khác 'unknown')
    - Vẫn không có -> 'unknown'
    """
    ln = str(row.get('level_norm')).strip().lower() if pd.notna(row.get('level_norm')) else 'unknown'
    ld = str(row.get('level_dashboard')).strip().lower() if pd.notna(row.get('level_dashboard')) else 'unknown'

    if ln not in ['unknown', '', 'nan']:
        return row.get('level_norm')
    elif ld not in ['unknown', '', 'nan']:
        return row.get('level_dashboard')
    else:
        return 'unknown'


def build_analysis_base(
    combine_clean_path: str = '../hr_pipeline_output/clean/combine_clean.csv',
    fact_skills_path: str = '../hr_pipeline_output/dashboard/fact_job_skills.csv',
    output_path: str = 'analysis_base.csv'
) -> pd.DataFrame:
    print(f"=== BƯỚC 0: TẠO BẢNG CƠ SỞ ANALYSIS_BASE ===")
    
    # 1. Bỏ tin trùng
    print(f"\n1. Đọc dữ liệu từ {combine_clean_path}...")
    df_combine = pd.read_csv(combine_clean_path)
    print(f"   Tổng số tin ban đầu: {len(df_combine):,}")

    base = df_combine[df_combine['is_duplicate'] == False].copy()
    print(f"   Số tin sau khi lọc is_duplicate == False: {len(base):,} (loại bỏ: {len(df_combine) - len(base):,})")
    assert len(base) == 1884, f"Lỗi: Số dòng mong đợi là 1884 nhưng nhận được {len(base)}"

    # 2. Tính lương trung tâm salary_mid_m
    print("\n2. Tính lương trung tâm salary_mid_m...")
    base['salary_mid_m'] = base.apply(calculate_salary_mid, axis=1)
    n_salary = base['salary_mid_m'].notna().sum()
    med_itviec = base[base['site'] == 'itviec']['salary_mid_m'].median()
    med_vnw = base[base['site'] == 'vietnamworks']['salary_mid_m'].median()
    print(f"   Số tin có lương tính được: {n_salary} (kỳ vọng ~422)")
    print(f"   Lương trung vị ITviec: {med_itviec:.2f} tr VNĐ (kỳ vọng ~42.50)")
    print(f"   Lương trung vị VietnamWorks: {med_vnw:.2f} tr VNĐ (kỳ vọng ~31.25)")

    # 3. Gắn vai trò và cấp bậc từ fact_job_skills
    print(f"\n3. Đọc dữ liệu kỹ năng và vai trò từ {fact_skills_path}...")
    df_skills = pd.read_csv(fact_skills_path)

    # Rút gọn còn đúng 1 dòng mỗi job_uid
    roles_dedup = df_skills[['job_uid', 'role_group', 'role_dashboard', 'level_dashboard']].drop_duplicates(subset=['job_uid'])
    print(f"   Số job_uid độc nhất trong fact_job_skills: {len(roles_dedup):,}")

    base = base.merge(roles_dedup, on='job_uid', how='left')
    assert len(base) == 1884, f"Lỗi sau khi nối vai trò: số dòng thay đổi thành {len(base)}"

    base['role_family'] = base['role_group'].fillna('Other').replace({'': 'Other'})
    base['level_final'] = base.apply(determine_final_level, axis=1)
    unknown_levels = (base['level_final'] == 'unknown').sum()
    print(f"   Số tin có level_final == 'unknown': {unknown_levels} (kỳ vọng ~205)")

    # 4. Chuẩn hoá thành phố và loại công ty
    print("\n4. Chuẩn hoá thành phố và tạo cột loại công ty...")
    base['city_norm'] = base['city'].fillna('Khác').replace({'': 'Khác'})
    base['company_type'] = np.nan  # Bước 1 sẽ điền sau

    # 5. Các cột kỹ năng
    print("\n5. Xử lý các cột kỹ năng (valid_job == True)...")
    valid_uids = set(base['job_uid'])
    sk_val = df_skills[(df_skills['valid_job'] == True) & (df_skills['job_uid'].isin(valid_uids))].copy()

    # Tìm danh sách kỹ năng có >= 30 tin tuyển dụng
    skill_job_counts = sk_val.groupby('skill')['job_uid'].nunique()
    top_skills = skill_job_counts[skill_job_counts >= 30].index.tolist()
    print(f"   Số kỹ năng có >= 30 tin tuyển dụng: {len(top_skills)} (kỳ vọng 63)")

    skill_to_sk = {s: 'sk_' + clean_skill_col_name(s) for s in top_skills}
    skill_to_w = {s: 'w_' + clean_skill_col_name(s) for s in top_skills}

    # 5a: Cột nhị phân 0/1
    top_sk_val = sk_val[sk_val['skill'].isin(top_skills)]
    pivot_sk = top_sk_val.pivot_table(
        index='job_uid',
        columns='skill',
        values='valid_job',
        aggfunc=lambda x: 1,
        fill_value=0
    )
    pivot_sk.columns = [skill_to_sk[c] for c in pivot_sk.columns]

    # 5b: Cột trọng số w_... (imp_weight cao nhất nếu lặp)
    pivot_w = top_sk_val.pivot_table(
        index='job_uid',
        columns='skill',
        values='imp_weight',
        aggfunc='max',
        fill_value=0.0
    )
    pivot_w.columns = [skill_to_w[c] for c in pivot_w.columns]

    # 5c: Bốn cột tổng hợp trên TẤT CẢ kỹ năng của tin
    agg_5c = sk_val.groupby('job_uid').agg(
        n_skills=('skill', 'nunique'),
        n_required=('importance', lambda s: (s == 'required').sum()),
        n_advanced=('proficiency', lambda s: (s == 'advanced').sum()),
        demand_score=('imp_weight', 'sum')
    ).reset_index()

    # Ghép các cột kỹ năng vào bảng nền
    base = base.merge(agg_5c, on='job_uid', how='left')
    base['n_skills'] = base['n_skills'].fillna(0).astype(int)
    base['n_required'] = base['n_required'].fillna(0).astype(int)
    base['n_advanced'] = base['n_advanced'].fillna(0).astype(int)
    base['demand_score'] = base['demand_score'].fillna(0.0)

    base = base.merge(pivot_sk, on='job_uid', how='left')
    for col in pivot_sk.columns:
        base[col] = base[col].fillna(0).astype(int)

    base = base.merge(pivot_w, on='job_uid', how='left')
    for col in pivot_w.columns:
        base[col] = base[col].fillna(0.0)

    # 6. Chọn cột theo thứ tự yêu cầu
    ident_cols = ['job_uid', 'company_canonical_id', 'company_canonical_name', 'title']
    meta_cols = ['site', 'text_quality', 'posted_date', 'city_norm', 'role_family', 'role_dashboard', 'level_final', 'company_type', 'exp_min_years']
    salary_cols = ['salary_mid_m']
    summary_cols = ['n_skills', 'n_required', 'n_advanced', 'demand_score']
    sk_cols = [skill_to_sk[s] for s in top_skills]
    w_cols = [skill_to_w[s] for s in top_skills]

    final_columns = ident_cols + meta_cols + salary_cols + summary_cols + sk_cols + w_cols
    analysis_base = base[final_columns].copy()

    # 7. Kiểm tra tính toàn vẹn (Validation Checks)
    print("\n7. KIỂM TRA TÍNH TOÀN VẸN (VALIDATION):")
    row_count = len(analysis_base)
    uid_unique = analysis_base['job_uid'].nunique() == row_count
    n_companies_ge_5 = (analysis_base['company_canonical_id'].value_counts() >= 5).sum()
    n_posted_date = analysis_base['posted_date'].notna().sum()
    n_cols = len(analysis_base.columns)

    # Kiểm tra sk_x == 1 <=> w_x > 0
    sk_w_match = True
    for s in top_skills:
        sk_c = skill_to_sk[s]
        w_c = skill_to_w[s]
        if not ((analysis_base[sk_c] == 1) == (analysis_base[w_c] > 0)).all():
            sk_w_match = False
            break

    print(f"   [1] Số dòng: {row_count} (Chuẩn: 1884) -> {'PASS' if row_count == 1884 else 'FAIL'}")
    print(f"   [2] job_uid không trùng: {uid_unique} -> {'PASS' if uid_unique else 'FAIL'}")
    print(f"   [3] Tin có lương: {n_salary} (Chuẩn: ~422) -> {'PASS' if n_salary == 422 else 'FAIL'}")
    print(f"   [4] Lương trung vị ITviec: {med_itviec:.2f} (Chuẩn: ~42.50) -> {'PASS' if abs(med_itviec - 42.5) < 0.1 else 'FAIL'}")
    print(f"       Lương trung vị VNW: {med_vnw:.2f} (Chuẩn: ~31.25) -> {'PASS' if abs(med_vnw - 31.25) < 0.1 else 'FAIL'}")
    print(f"   [5] Công ty >= 5 tin: {n_companies_ge_5} (Chuẩn: 79) -> {'PASS' if n_companies_ge_5 == 79 else 'FAIL'}")
    print(f"   [6] Tin có posted_date: {n_posted_date} (Chuẩn: 957) -> {'PASS' if n_posted_date == 957 else 'FAIL'}")
    print(f"   [7] Tổng số cột: {n_cols} (Chuẩn: ~144) -> {'PASS' if n_cols == 144 else 'FAIL'}")
    print(f"   [8] sk_x == 1 <=> w_x > 0 cho mọi dòng: {sk_w_match} -> {'PASS' if sk_w_match else 'FAIL'}")

    # Lưu kết quả
    print(f"\nLưu file kết quả tại: {output_path} (mã hoá utf-8-sig)...")
    analysis_base.to_csv(output_path, index=False, encoding='utf-8-sig')
    print("HOÀN TẤT BƯỚC 0 THÀNH CÔNG!")
    
    return analysis_base


if __name__ == '__main__':
    # Determine base directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))

    combine_clean_csv = os.path.join(project_root, 'hr_pipeline_output', 'clean', 'combine_clean.csv')
    fact_skills_csv = os.path.join(project_root, 'hr_pipeline_output', 'dashboard', 'fact_job_skills.csv')
    output_csv = os.path.join(script_dir, 'analysis_base.csv')

    build_analysis_base(
        combine_clean_path=combine_clean_csv,
        fact_skills_path=fact_skills_csv,
        output_path=output_csv
    )
