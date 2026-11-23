"""Create dashboard-ready star-schema CSVs from combine_clean and job_skill_level.

Handles:
- Fact & Dimension modeling (fact_jobs, fact_job_skills, dim_companies)
- Separation of range/exact from floor ('from') and ceiling ('up_to') salaries
- Sample size thresholding (n >= 5) on salary benchmarks with sample_warning
- 2-tier skill demand indexing (overall, by technical family, and by role)
- Human verification audit flagging (needs_human_check)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


ROLE_RULES = [
    ('solution_architecture', r'\b(?:solution architect|solutions architect|software architect|enterprise architect|technical architect|system architect|principal architect|chief architect)\b'),
    ('project_product_management', r'\b(?:project manager|product manager|product owner|scrum master|program manager|delivery manager|pmo|engineering manager|head of engineering|director of engineering|technical leader|tech lead|technical lead|project leader|it technical director|chief technology officer|\bcto\b|\bcio\b|trưởng dự án|quản lý dự án|quản lý sản phẩm|trưởng phòng công nghệ)\b'),
    ('uiux_design', r'\b(?:ui/ux|ux/ui|ux designer|ui designer|product designer|graphic designer|concept artist|thiết kế giao diện)\b'),
    ('erp_crm', r'\b(?:erp consultant|sap consultant|crm consultant|salesforce developer|salesforce|sap developer|dynamics 365|oracle consultant|presales|application consultant|servicenow|core banking)\b'),
    ('data_scientist_ai', r'\b(?:data scientist|machine learning|ml engineer|ai engineer|ai specialist|nlp|computer vision|llm engineer|ai solutions|generative ai|\bai\b|genai|deep learning)\b'),
    ('data_engineer', r'\b(?:data engineer|etl engineer|data platform|database engineer|big data engineer|data warehouse)\b'),
    ('data_analyst_bi', r'\b(?:data analyst|bi analyst|business intelligence|power bi|analytics engineer|quản trị dữ liệu|data governance|data quality)\b'),
    ('business_analyst', r'\b(?:business analyst|business analysis|system analyst|business systems analyst|\bba\b|phân tích nghiệp vụ|bridge system engineer|bse\b|brse\b)\b'),
    ('qa_tester', r'\b(?:qa|qc|tester|testing|quality assurance|quality control|sdet|kiểm thử|test engineer|automation test|manual test)\b'),
    ('security', r'\b(?:security|cybersecurity|soc analyst|pentest|penetration test|an ninh mạng|bảo mật|information security)\b'),
    ('devops_cloud', r'\b(?:devops|sre|site reliability|cloud engineer|cloud architect|platform engineer|aws engineer|azure engineer|kỹ sư giải pháp cloud|cloud)\b'),
    ('mobile', r'\b(?:android|ios developer|ios engineer|flutter|react native|mobile developer|mobile engineer|swift developer|kotlin developer)\b'),
    ('fullstack', r'\b(?:full.?stack|full stack)\b'),
    ('frontend', r'\b(?:front.?end|frontend|react developer|reactjs|vue developer|vuejs|angular developer|web developer|frontend engineer)\b'),
    ('backend', r'\b(?:back.?end|backend|java developer|java engineer|\bjava\b|python developer|python engineer|\bpython\b|golang developer|golang engineer|\bgolang\b|\.net developer|\.net engineer|\.net developers|\.net|\bc#\b|c\+\+ developer|c\+\+ engineer|\bc\+\+\b|php developer|php engineer|\bphp\b|nodejs developer|nodejs engineer|ruby developer|backend engineer|backend & platform)\b'),
    ('embedded_hardware', r'\b(?:embedded|firmware|hardware engineer|vi mạch|soc bsp|iot engineer|posix kernel|semiconductor)\b'),
    ('game_dev', r'\b(?:game developer|unity developer|unreal engine|game programmer|game)\b'),
    ('system_network', r'\b(?:system admin|sysadmin|network engineer|infrastructure engineer|it support|helpdesk|it administrator|system engineer|systems administrator|it officer|kỹ sư hệ thống|call center engineer)\b'),
    ('general_software_eng', r'\b(?:software engineer|software developer|software specialist|lập trình viên|kỹ sư phần mềm|thực tập sinh lập trình|developer|developers)\b'),
]

TYPE_RULES = [
    ('outsourcing_service', r'\b(?:outsourc|offshore|it service|consulting|dịch vụ phần mềm|gia công phần mềm)\b'),
    ('product_technology', r'\b(?:it product|product company|saas|software product|sản phẩm phần mềm)\b'),
]


def role_from_title(title):
    s = str(title).lower()
    hits = [name for name, expr in ROLE_RULES if re.search(expr, s)]
    if not hits:
        return 'other'
    if len(hits) == 1:
        return hits[0]

    # Priority resolution for compound matches
    if 'solution_architecture' in hits:
        return 'solution_architecture'
    if 'project_product_management' in hits and not ('backend' in hits or 'fullstack' in hits):
        return 'project_product_management'
    if 'qa_tester' in hits:
        return 'qa_tester'
    if 'fullstack' in hits:
        return 'fullstack'
    if 'data_scientist_ai' in hits:
        return 'data_scientist_ai'
    if 'devops_cloud' in hits:
        return 'devops_cloud'
    if 'mobile' in hits:
        return 'mobile'
    if 'frontend' in hits:
        return 'frontend'
    if 'backend' in hits:
        return 'backend'
    if 'business_analyst' in hits:
        return 'business_analyst'
    if 'embedded_hardware' in hits:
        return 'embedded_hardware'
    if 'system_network' in hits:
        return 'system_network'

    specific = [h for h in hits if h != 'general_software_eng']
    return specific[0] if specific else 'general_software_eng'


def classify_role_group(title, skills='', job_function=''):
    """Classifies job into 15 canonical role groups using hierarchical rules and skill fallbacks.
    
    Returns:
        tuple[str, str, str]: (role_group, role_source, role_confidence)
          role_group in {'Backend', 'Frontend', 'Fullstack', 'Mobile', 'Data / AI',
                         'DevOps / Cloud / SysAdmin', 'QA / QC / Tester', 'BA / PO / PM',
                         'Security', 'IT Support / ERP', 'Management / Leadership',
                         'UI / UX Design', 'Embedded / Hardware / Telecom', 'Game Dev', 'Other'}
          role_source in {'title', 'skills', 'job_function', 'unknown'}
          role_confidence in {'high', 'medium', 'low'}
    """
    t = str(title).lower() if pd.notna(title) else ''
    s = str(skills).lower() if pd.notna(skills) else ''
    jf_str = str(job_function).lower() if pd.notna(job_function) else ''

    # 1. Security
    if re.search(r'\b(?:security|cybersecurity|soc(?:\s|analyst)|pentest|penetration test(?:er)?|an ninh mạng|bảo mật|infosec|information security|it risk)\b', t):
        return 'Security', 'title', 'high'

    # 2. QA / QC / Tester
    if re.search(r'\b(?:qa|qc|tester|testing|quality assurance|quality control|\bsdet\b|kiểm thử|test engineer|test automation|automation test|manual test)\b', t):
        return 'QA / QC / Tester', 'title', 'high'

    # 3. Mobile
    if re.search(r'\b(?:ios developer|ios engineer|\bios\b|android developer|android engineer|\bandroid\b|flutter|react native|mobile developer|mobile engineer|swift developer|kotlin developer|mobile architect)\b', t):
        return 'Mobile', 'title', 'high'

    # 4. Fullstack
    if re.search(r'\b(?:full.?stack|full stack|full-stack)\b', t):
        return 'Fullstack', 'title', 'high'

    # 5. Frontend
    if re.search(r'\b(?:front.?end|frontend|react developer|reactjs developer|vue developer|vuejs developer|angular developer|web developer|frontend engineer)\b', t):
        return 'Frontend', 'title', 'high'

    # 6. BA / PO / PM
    if re.search(r'\b(?:business analyst|business analysis|system analyst|\bba\b|product owner|project manager|project leader|program manager|delivery manager|\bscrum master\b|\bpmo\b|quản lý dự án|quản lý sản phẩm|phân tích nghiệp vụ|bridge system engineer|\bbse\b|\bbrse\b)\b', t):
        return 'BA / PO / PM', 'title', 'high'

    # 7. Data / AI (Strict boundary: explicit data/ML/AI roles)
    if re.search(r'\b(?:data science|data scientist|machine learning|\bml engineer\b|ai engineer|ai specialist|ai researcher|deep learning|computer vision|\bnlp\b|data engineer|data platform|data warehouse|big data|etl|data analyst|bi analyst|business intelligence|power bi|\bdba\b|database administrator|database engineer|database expert|kỹ sư dữ liệu|kỹ sư ai|head of ai|head of data|ai lead|applied ai|ai architect)\b', t):
        return 'Data / AI', 'title', 'high'

    # 8. DevOps / Cloud / SysAdmin
    if re.search(r'\b(?:devops|devsecops|\bsre\b|site reliability|cloud engineer|cloud architect|cloud|aws engineer|azure engineer|gcp|sysadmin|system admin|systems administrator|system administrator|system engineer|network engineer|infrastructure engineer|kỹ sư hệ thống|quản trị mạng|sysops)\b', t):
        return 'DevOps / Cloud / SysAdmin', 'title', 'high'

    # 9. UI / UX Design
    if re.search(r'\b(?:ui/ux|ux/ui|ux designer|ui designer|product designer|graphic designer|concept artist|thiết kế giao diện)\b', t):
        return 'UI / UX Design', 'title', 'high'

    # 10. Embedded / Hardware / Telecom
    if re.search(r'\b(?:embedded|firmware|hardware engineer|vi mạch|soc bsp|iot engineer|semiconductor|telecom|viễn thông|rf engineer|audio engineer)\b', t):
        return 'Embedded / Hardware / Telecom', 'title', 'high'

    # 11. Game Dev
    if re.search(r'\b(?:game developer|unity developer|unreal engine|game programmer|game)\b', t):
        return 'Game Dev', 'title', 'high'

    # 12. IT Support / ERP
    if re.search(r'\b(?:it support|helpdesk|desktop support|it officer|customer support|kỹ thuật viên it|hỗ trợ kỹ thuật|erp|sap|salesforce|crm|dynamics 365|dms|oracle apps|application consultant)\b', t):
        return 'IT Support / ERP', 'title', 'high'

    # 13. Backend
    if re.search(r'\b(?:back.?end|backend|\bjava\b(?!script)|\bpython\b|\bgolang\b|\bgo engineer\b|\.net|\bc#\b|\bc\+\+\b|\bphp\b|nodejs|node\.js|\bruby\b|backend engineer|solution architect|solutions architect|software architect|system architect|tech lead|technical lead)\b', t):
        return 'Backend', 'title', 'high'

    # 14. Leadership (Strict C-level / general IT management)
    if re.search(r'\b(?:chief technology officer|\bcto\b|\bcio\b|head of it|director of it|it director|director of engineering|vp of engineering|engineering manager|it manager|trưởng phòng it|giám đốc công nghệ|quản lý it)\b', t):
        return 'Management / Leadership', 'title', 'high'

    # Fallback for generic dev titles using skills
    is_generic_dev = bool(re.search(r'\b(?:software engineer|software developer|developer|lập trình viên|kỹ sư phần mềm|chuyên viên phát triển phần mềm|thực tập sinh lập trình|it specialist)\b', t))
    if is_generic_dev:
        if re.search(r'\b(?:reactjs|vuejs|angular)\b', s) and not re.search(r'\b(?:java|python|\.net|php|golang|nodejs)\b', s):
            return 'Frontend', 'skills', 'medium'
        if re.search(r'\b(?:reactjs|vuejs|angular)\b', s) and re.search(r'\b(?:java|python|\.net|php|golang|nodejs)\b', s):
            return 'Fullstack', 'skills', 'medium'
        if re.search(r'\b(?:flutter|react native|ios|android|swift|kotlin)\b', s):
            return 'Mobile', 'skills', 'medium'
        if re.search(r'\b(?:spring boot|django|fastapi|laravel|asp\.net|\.net core|expressjs|ruby on rails)\b', s):
            return 'Backend', 'skills', 'medium'
        if re.search(r'\b(?:machine learning|deep learning|tensorflow|pytorch|nlp|computer vision)\b', s):
            return 'Data / AI', 'skills', 'medium'
        if re.search(r'\b(?:kubernetes|docker|terraform|ansible|jenkins|ci/cd|aws|azure|gcp)\b', s) and not re.search(r'\b(?:java|python|c#|\.net)\b', s):
            return 'DevOps / Cloud / SysAdmin', 'skills', 'medium'
        if re.search(r'\b(?:selenium|cypress|jmeter|automation testing|appium)\b', s):
            return 'QA / QC / Tester', 'skills', 'medium'
        return 'Backend', 'title', 'low'

    # VietnamWorks secondary signal (job_function)
    if 'qa/qc' in jf_str or 'testing' in jf_str:
        return 'QA / QC / Tester', 'job_function', 'medium'
    if 'database' in jf_str or 'data engineer' in jf_str or 'analyst/ai' in jf_str:
        return 'Data / AI', 'job_function', 'medium'
    if 'security' in jf_str:
        return 'Security', 'job_function', 'medium'

    return 'Other', 'unknown', 'low'


def size_bucket(n):
    if pd.isna(n) or n <= 0:
        return 'unknown'
    if n < 50:
        return '1-49'
    if n < 250:
        return '50-249'
    if n < 1000:
        return '250-999'
    return '1000+'


def segment_company_type(values):
    text = ' '.join(str(v).lower() for v in values if pd.notna(v) and str(v).strip())
    hits = [label for label, rx in TYPE_RULES if re.search(rx, text)]
    return (hits[0], 'reported_platform_type') if len(set(hits)) == 1 else ('unknown', 'not_verified')


def _date_str(df, col):
    return pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')


def build_skill_demand_index(jobs, skill_fact, out):
    """Transparent cross-sectional 0-100 index, with 2-tier family segmentation."""
    observations = jobs.loc[jobs.valid_job & jobs.event_date.notna(), 'event_date']
    if observations.empty:
        return {'index_as_of': None, 'growth_available': False}
    last_day = pd.to_datetime(observations.max())
    start = last_day - pd.Timedelta(days=29)
    previous_start = last_day - pd.Timedelta(days=59)
    present = set(pd.to_datetime(observations.unique()))
    current_coverage = sum((start + pd.Timedelta(days=i)) in present for i in range(30))
    prior_coverage = sum((previous_start + pd.Timedelta(days=i)) in present for i in range(30))
    has_growth = current_coverage >= 27 and prior_coverage >= 27

    sk = skill_fact[skill_fact.valid_job.eq(True) & skill_fact.skill.notna()].copy()
    sk['event_date'] = pd.to_datetime(sk.event_date, errors='coerce')
    sk = sk.merge(jobs[['job_uid', 'size_bucket']], on='job_uid', how='left', validate='many_to_one')

    current = sk[(sk.event_date >= start) & (sk.event_date <= last_day)]
    previous = sk[(sk.event_date >= previous_start) & (sk.event_date < start)]

    windows = [('all', current, previous)]

    # Segment by Technical Family (isolating Programming Languages, Frameworks, Cloud, etc.)
    if 'skill_family' in current.columns:
        for fam, part in current.groupby('skill_family', dropna=False):
            if fam and str(fam) != 'nan' and str(fam) != 'unknown':
                old = previous[previous['skill_family'].eq(fam)]
                windows.append((f"family:{fam}", part, old))

    for column, prefix in [('role_group', 'role:'), ('size_bucket', 'size:')]:
        for value, part in current.groupby(column, dropna=False):
            old = previous[previous[column].eq(value)]
            windows.append((prefix + str(value), part, old))

    output = []
    for segment, frame, old in windows:
        if frame.empty:
            continue
        tab = frame.groupby('skill').agg(
            job_count=('job_uid', 'nunique'),
            company_count=('company_canonical_id', 'nunique'),
            required_count=('importance', lambda s: int((s == 'required').sum())),
            needs_review_count=('needs_human_check', lambda s: int(s.fillna(False).astype(bool).sum()) if 'needs_human_check' in frame.columns else 0)
        ).reset_index()

        tab['required_share'] = (tab.required_count / tab.job_count).round(3)
        tab['job_percentile'] = tab.job_count.rank(pct=True, method='average')
        tab['company_percentile'] = tab.company_count.rank(pct=True, method='average')
        tab['index_0_100'] = (100 * (.45 * tab.job_percentile + .35 * tab.company_percentile
                                    + .20 * tab.required_share)).round(1)
        # Sensitivity analysis alternative weight formulations
        tab['index_balanced_weights'] = (100 * (.34 * tab.job_percentile + .33 * tab.company_percentile
                                               + .33 * tab.required_share)).round(1)
        tab['index_volume_weights'] = (100 * (.60 * tab.job_percentile + .25 * tab.company_percentile
                                             + .15 * tab.required_share)).round(1)
        tab['segment'] = segment
        tab['as_of'] = last_day.strftime('%Y-%m-%d')
        tab['period_start'] = start.strftime('%Y-%m-%d')

        if has_growth:
            prior_count = old.groupby('skill').job_uid.nunique()
            tab['prior_30d_jobs'] = tab.skill.map(prior_count).fillna(0).astype(int)
            tab['growth_30d_pct'] = ((tab.job_count - tab.prior_30d_jobs) /
                                     tab.prior_30d_jobs.replace(0, float('nan')) * 100).round(1)
        else:
            tab['prior_30d_jobs'] = float('nan')
            tab['growth_30d_pct'] = float('nan')

        tab['growth_available'] = has_growth
        tab['coverage_days_current_30'] = current_coverage
        tab['coverage_days_previous_30'] = prior_coverage
        tab['reliability'] = 'limited_coverage' if current_coverage < 27 else 'observed_coverage'
        tab['sample_warning'] = tab.job_count.lt(5)
        output.append(tab)

    index = pd.concat(output, ignore_index=True)
    index.sort_values(['segment', 'index_0_100'], ascending=[True, False]).to_csv(
        out / 'skill_demand_index.csv', index=False, encoding='utf-8-sig')

    return {'index_as_of': last_day.strftime('%Y-%m-%d'),
            'growth_available': has_growth,
            'coverage_days_current_30': current_coverage,
            'coverage_days_previous_30': prior_coverage,
            'index_rows': len(index)}


def run(clean_path: Path, skill_path: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    jobs = pd.read_csv(clean_path, low_memory=False)
    skills = pd.read_csv(skill_path, low_memory=False)

    if jobs.job_uid.duplicated().any():
        raise ValueError('Job UID not unique: require one row per source job UID')

    jobs['role_dashboard'] = jobs.title.fillna('').map(role_from_title)
    
    # Canonical role group classification with source & confidence
    skills_series = jobs['skills'] if 'skills' in jobs.columns else pd.Series('', index=jobs.index)
    jf_series = jobs['job_function'] if 'job_function' in jobs.columns else pd.Series('', index=jobs.index)
    
    role_tuples = [
        classify_role_group(t, s, jf)
        for t, s, jf in zip(jobs['title'], skills_series, jf_series)
    ]
    jobs['role_group'] = [r[0] for r in role_tuples]
    jobs['role_source'] = [r[1] for r in role_tuples]
    jobs['role_confidence'] = [r[2] for r in role_tuples]

    jobs['level_dashboard'] = jobs['level_norm'].replace('unknown', None).fillna(jobs.get('level_inferred_exp')).fillna('unknown')

    if 'company_size' in jobs:
        jobs['size_bucket'] = pd.to_numeric(jobs['company_size'], errors='coerce').map(size_bucket).fillna('unknown')
    else:
        jobs['size_bucket'] = 'unknown'

    if 'company_type' not in jobs:
        jobs['company_type'] = ''

    for date_field in ['posted_date', 'first_seen', 'last_seen']:
        if date_field not in jobs:
            jobs[date_field] = ''
        jobs[date_field] = _date_str(jobs, date_field)

    jobs['posted_month'] = jobs.posted_date.str.slice(0, 7)
    jobs['observed_month'] = jobs.first_seen.str.slice(0, 7)
    jobs['event_date'] = jobs.first_seen.fillna(jobs.posted_date)
    jobs['event_month'] = jobs.event_date.str.slice(0, 7)
    jobs['valid_job'] = ~jobs.is_duplicate.fillna(False).astype(bool)

    jobs['salary_min_m'] = pd.to_numeric(jobs.salary_min_m, errors='coerce')
    jobs['salary_max_m'] = pd.to_numeric(jobs.salary_max_m, errors='coerce')

    # Strict separation: range & exact are comparable for midpoints; from/up_to are separate
    is_range_exact = jobs['salary_type_norm'].isin(['range', 'exact'])
    jobs['salary_reliable'] = (
        jobs.valid_job
        & ~jobs.salary_can_xem.fillna(False).astype(bool)
        & is_range_exact
        & jobs.salary_min_m.gt(0)
        & jobs.salary_max_m.gt(0)
        & jobs.salary_max_m.ge(jobs.salary_min_m)
    )
    jobs['salary_mid_m'] = (jobs['salary_min_m'] + jobs['salary_max_m']) / 2
    jobs.loc[~jobs['salary_reliable'], 'salary_mid_m'] = float('nan')

    jobs['salary_floor_reliable'] = (
        jobs.valid_job
        & ~jobs.salary_can_xem.fillna(False).astype(bool)
        & jobs['salary_type_norm'].eq('from')
        & jobs.salary_min_m.gt(0)
    )
    jobs['salary_ceiling_reliable'] = (
        jobs.valid_job
        & ~jobs.salary_can_xem.fillna(False).astype(bool)
        & jobs['salary_type_norm'].eq('up_to')
        & jobs.salary_max_m.gt(0)
    )

    # Filter intern / fresher salary outliers > 30m VND/month
    is_intern_fresher = jobs['level_dashboard'].isin(['intern', 'fresher'])
    jobs.loc[is_intern_fresher & (jobs['salary_mid_m'] > 30.0), 'salary_reliable'] = False
    jobs.loc[is_intern_fresher & (jobs['salary_mid_m'] > 30.0), 'salary_mid_m'] = float('nan')
    jobs.loc[is_intern_fresher & (jobs['salary_min_m'] > 30.0), 'salary_floor_reliable'] = False
    jobs.loc[is_intern_fresher & (jobs['salary_max_m'] > 30.0), 'salary_ceiling_reliable'] = False

    # Save Dimensions and Fact Jobs
    columns = [
        'job_uid', 'site', 'title', 'company', 'company_canonical_id', 'company_canonical_name',
        'city', 'role_group', 'role_source', 'role_confidence', 'role_dashboard', 'level_dashboard', 'size_bucket', 'company_type',
        'posted_date', 'first_seen', 'last_seen', 'event_date', 'event_month',
        'valid_job', 'is_duplicate', 'n_postings_in_group', 'left_censored', 'right_censored',
        'text_source', 'text_quality',
        'salary_type_norm', 'salary_tax_type', 'salary_min_m', 'salary_max_m',
        'salary_mid_m', 'salary_reliable', 'exp_min_years', 'exp_max_years'
    ]
    avail_cols = [c for c in columns if c in jobs.columns]
    jobs[avail_cols].to_csv(out / 'fact_jobs.csv', index=False, encoding='utf-8-sig')

    for col in ['valid_job', 'role_group', 'role_dashboard', 'level_dashboard', 'event_date', 'event_month', 'company_canonical_id']:
        if col in skills.columns:
            skills = skills.drop(columns=[col])

    skill_fact = skills.merge(
        jobs[['job_uid', 'company_canonical_id', 'role_group', 'role_dashboard', 'level_dashboard', 'event_date', 'event_month', 'valid_job']],
        on='job_uid', how='left', validate='many_to_one'
    )
    skill_fact = skill_fact.drop_duplicates(['job_uid', 'skill'])
    skill_cols_to_keep = [
        'job_uid', 'skill', 'skill_raw', 'skill_family', 'skill_category',
        'needs_human_check', 'importance', 'proficiency', 'prof_score', 'imp_weight', 'match_weight',
        'company_canonical_id', 'role_group', 'role_dashboard', 'level_dashboard', 'event_date', 'event_month', 'valid_job'
    ]
    avail_skill_cols = [c for c in skill_cols_to_keep if c in skill_fact.columns]
    skill_fact = skill_fact[avail_skill_cols]
    skill_fact.to_csv(out / 'fact_job_skills.csv', index=False, encoding='utf-8-sig')

    valid_jobs = jobs[jobs.valid_job & jobs.event_date.notna()].copy()
    valid_skills = skill_fact[skill_fact.valid_job.eq(True) & skill_fact.event_date.notna()].copy()

    def trend(period, name):
        valid_jobs.groupby([period, 'role_group'], dropna=False).agg(
            new_jobs=('job_uid', 'nunique'), companies=('company_canonical_id', 'nunique')
        ).reset_index().to_csv(out / f'role_trend_{name}.csv', index=False, encoding='utf-8-sig')
        valid_skills.groupby([period, 'skill'], dropna=False).agg(
            new_jobs=('job_uid', 'nunique'), companies=('company_canonical_id', 'nunique'),
            required_jobs=('importance', lambda x: (x == 'required').sum())
        ).reset_index().to_csv(out / f'skill_trend_{name}.csv', index=False, encoding='utf-8-sig')
    trend('event_date', 'daily')
    trend('event_month', 'monthly')

    # Salary Benchmarks with threshold n >= 5 and clean separation of range vs from vs up_to
    # Primary grouping is role_group + level_dashboard
    pay = jobs[(jobs.salary_reliable | jobs.salary_floor_reliable | jobs.salary_ceiling_reliable) & jobs.role_group.ne('Other')].copy()

    benchmarks = pay.groupby(['role_group', 'level_dashboard'], dropna=False).agg(
        n_salary_jobs=('job_uid', 'nunique'),
        n_range_jobs=('salary_mid_m', lambda s: int(s.notna().sum())),
        median_range_mid_m=('salary_mid_m', lambda s: round(float(s.dropna().median()), 2) if len(s.dropna()) >= 5 else float('nan')),
        p25_range_mid_m=('salary_mid_m', lambda x: round(float(x.dropna().quantile(.25)), 2) if len(x.dropna()) >= 5 else float('nan')),
        p75_range_mid_m=('salary_mid_m', lambda x: round(float(x.dropna().quantile(.75)), 2) if len(x.dropna()) >= 5 else float('nan')),
        n_floor_from_jobs=('salary_floor_reliable', lambda s: int(s.sum())),
        median_floor_from_m=('salary_min_m', lambda s: round(float(s[pay.loc[s.index, 'salary_floor_reliable']].median()), 2) if int(pay.loc[s.index, 'salary_floor_reliable'].sum()) >= 5 else float('nan')),
        n_ceiling_upto_jobs=('salary_ceiling_reliable', lambda s: int(s.sum())),
        median_ceiling_upto_m=('salary_max_m', lambda s: round(float(s[pay.loc[s.index, 'salary_ceiling_reliable']].median()), 2) if int(pay.loc[s.index, 'salary_ceiling_reliable'].sum()) >= 5 else float('nan'))
    ).reset_index()

    benchmarks['sample_warning_range'] = benchmarks['n_range_jobs'] < 5
    benchmarks['sample_warning_from'] = benchmarks['n_floor_from_jobs'] < 5
    benchmarks['sample_warning_upto'] = benchmarks['n_ceiling_upto_jobs'] < 5
    benchmarks['sample_warning'] = benchmarks['n_range_jobs'] < 5
    benchmarks['usd_vnd_rate'] = 25000
    benchmarks['working_days_month'] = 22
    benchmarks['note_ceiling_upto'] = "Advertised maximum ceiling, not expected paid median"
    benchmarks.to_csv(out / 'salary_benchmarks.csv', index=False, encoding='utf-8-sig')

    # Monthly salary trends (only range & exact)
    pay_range = jobs[jobs.salary_reliable & jobs.event_month.notna()].copy()
    pay_range.groupby(['event_month', 'role_group', 'level_dashboard']).agg(
        n_salary_jobs=('job_uid', 'nunique'), median_salary_mid_m=('salary_mid_m', 'median')
    ).reset_index().to_csv(out / 'salary_monthly.csv', index=False, encoding='utf-8-sig')

    company_rows = []
    for cid, rows in jobs[jobs.valid_job].groupby('company_canonical_id'):
        direct, source = segment_company_type(rows.company_type.dropna())
        role_counts = rows.role_group.value_counts()
        top_role = role_counts.index[0] if len(role_counts) else 'Other'
        share = round(float(role_counts.iloc[0] / len(rows)), 3) if len(role_counts) else None
        enough = len(rows) >= 5
        focus = ('ai_data_hiring' if top_role in {'Data / AI'} else
                 'software_engineering_hiring' if top_role in {'Backend', 'Frontend', 'Fullstack', 'Mobile'} else
                 'infrastructure_security_hiring' if top_role in {'DevOps / Cloud / SysAdmin', 'Security'} else
                 'business_quality_hiring' if top_role in {'BA / PO / PM', 'QA / QC / Tester'} else
                 'product_project_management_hiring' if top_role in {'BA / PO / PM', 'Management / Leadership'} else
                 'design_hiring' if top_role in {'UI / UX Design'} else 'other_hiring') if enough and share >= .4 else 'undetermined'
        company_rows.append({
            'company_canonical_id': cid,
            'company_canonical_name': rows.company_canonical_name.iloc[0],
            'company_type_reported': direct,
            'company_type_evidence': source,
            'company_size_bucket': rows.size_bucket.mode().iloc[0] if not rows.size_bucket.mode().empty else 'unknown',
            'observed_jobs': len(rows),
            'distinct_role_groups': int(rows.role_group.nunique()),
            'top_hiring_role': top_role,
            'top_hiring_role_share': share,
            'hiring_focus_inferred': focus,
            'hiring_profile': 'specialized_hiring' if len(rows) >= 5 and share >= .65 else
                              'diverse_hiring' if len(rows) >= 5 and rows.role_group.nunique() >= 4 else
                              'insufficient_evidence',
            'profile_is_inference': True,
            'hiring_focus_confidence': 'low' if not enough else 'medium',
            'last_seen': rows.last_seen.dropna().max() if rows.last_seen.notna().any() else '',
        })
    pd.DataFrame(company_rows).to_csv(out / 'dim_companies.csv', index=False, encoding='utf-8-sig')

    demand_index_status = build_skill_demand_index(jobs, skill_fact, out)

    days = valid_jobs.event_date.dropna().nunique()
    site_pay = jobs[jobs.salary_reliable].groupby('site')['job_uid'].count().to_dict()
    tax_pay = jobs[jobs.salary_reliable]['salary_tax_type'].value_counts().to_dict()

    metrics = {
        'unique_source_jobs': len(jobs),
        'deduplicated_jobs': int(jobs.valid_job.sum()),
        'event_days_present': int(days),
        'events_without_dates': int((jobs.valid_job & jobs.event_date.isna()).sum()),
        'salary_range_comparable_jobs': int(jobs.salary_reliable.sum()),
        'salary_floor_jobs': int(jobs.salary_floor_reliable.sum()),
        'salary_ceiling_jobs': int(jobs.salary_ceiling_reliable.sum()),
        'salary_comparable_share': round(float(jobs.salary_reliable.sum() / max(1, jobs.valid_job.sum())), 3),
        'salary_site_breakdown': site_pay,
        'salary_tax_type_breakdown': tax_pay,
        'skill_fact_pairs': len(skill_fact),
        'company_segments_are_inferred': True,
        'role_group_distribution': valid_jobs['role_group'].value_counts().to_dict(),
        'role_source_distribution': valid_jobs['role_source'].value_counts().to_dict(),
        'role_confidence_distribution': valid_jobs['role_confidence'].value_counts().to_dict(),
        'skill_demand_index': demand_index_status,
        'skill_demand_index_weights': {
            'default': {'postings_volume': 0.45, 'company_breadth': 0.35, 'required_intensity': 0.20},
            'balanced_alternative': {'postings_volume': 0.34, 'company_breadth': 0.33, 'required_intensity': 0.33},
            'volume_alternative': {'postings_volume': 0.60, 'company_breadth': 0.25, 'required_intensity': 0.15}
        },
        'assumptions': {
            'usd_vnd_rate': 25000,
            'working_days_month': 22,
            'salary_ceiling_note': 'up_to represents advertised maximum ceiling, not expected paid median'
        },
        'trend_metric_definition': 'unique deduplicated jobs first observed (first_seen, fallback posted_date)',
        'limitation': 'Observed 15-day snapshot window (left-censored before 2026-10-11, right-censored if active on 2026-10-25). Salary benchmarks suppress n<5.'
    }
    (out / 'dashboard_quality.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--clean', type=Path, default=Path('hr_pipeline_output/clean/combine_clean.csv'))
    p.add_argument('--skills', type=Path, default=Path('hr_pipeline_output/clean/job_skill_level.csv'))
    p.add_argument('--out', type=Path, default=Path('hr_pipeline_output/dashboard'))
    a = p.parse_args()
    run(a.clean, a.skills, a.out)
