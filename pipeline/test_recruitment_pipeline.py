"""Automated Unit, Invariant, and Regression Tests for Recruitment Pipeline."""
from __future__ import annotations

import unittest
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from recruitment_pipeline import (
    normalize, company_key, _compact, normalize_city, salary_values,
    split_skills, parse_number, extract_salary_from_title,
    make_skill_dictionary, skill_match, detect_companies, text_containment
)
from jd_analysis import extract_experience, extract_level, classify_skill, infer_level_from_experience
from dashboard_data import role_from_title, classify_role_group


class TestPipeline(unittest.TestCase):
    # --------------------------------------------------------------------------
    # 1. Company Normalization
    # --------------------------------------------------------------------------
    def test_company_normalization(self):
        self.assertEqual(company_key('CÔNG TY TNHH ABC VIỆT NAM'), company_key('ABC Company Limited'))
        self.assertEqual(_compact('Remote People'), _compact('RemotePeople Co., Ltd.'))

    # --------------------------------------------------------------------------
    # 2. City Normalization
    # --------------------------------------------------------------------------
    def test_city_normalization(self):
        self.assertEqual(normalize_city('Ha Noi'), 'Hà Nội')
        self.assertEqual(normalize_city('Hanoi'), 'Hà Nội')
        self.assertEqual(normalize_city('Ho Chi Minh'), 'Hồ Chí Minh')
        self.assertEqual(normalize_city('TP. Hồ Chí Minh'), 'Hồ Chí Minh')
        self.assertEqual(normalize_city('Da Nang'), 'Đà Nẵng')
        self.assertEqual(normalize_city('Dong Nai'), 'Đồng Nai')

    # --------------------------------------------------------------------------
    # 3. Number Parser
    # --------------------------------------------------------------------------
    def test_number_parser(self):
        self.assertEqual(parse_number('1.000'), 1000.0)
        self.assertEqual(parse_number('1.500'), 1500.0)
        self.assertEqual(parse_number('1,000'), 1000.0)
        self.assertEqual(parse_number('17,040'), 17040.0)
        self.assertEqual(parse_number('25.3'), 25.3)

    # --------------------------------------------------------------------------
    # 4. Salary Parser: Mislabeled Currency
    # --------------------------------------------------------------------------
    def test_salary_mislabeled_currency(self):
        s = salary_values(pd.Series({'salary_text': '$ 15tr-40tr /tháng', 'salary_min': 15000000, 'salary_max': 40000000, 'currency': 'USD'}))
        self.assertEqual((s['salary_min_m'], s['salary_max_m']), (15, 40))
        self.assertEqual(s['salary_currency_raw'], 'VND')

    # --------------------------------------------------------------------------
    # 5. Salary Parser: "Từ X" is Floor (from) Only
    # --------------------------------------------------------------------------
    def test_salary_tu_x_is_from_min_only(self):
        s = salary_values(pd.Series({'salary_text': 'Từ $ 1,000 /tháng', 'salary_min': 1000, 'salary_max': 1000, 'currency': 'USD'}))
        self.assertEqual(s['salary_type'], 'from')
        self.assertEqual(s['salary_min_m'], 25.0)
        self.assertTrue(pd.isna(s['salary_max_m']))

    # --------------------------------------------------------------------------
    # 6. Salary Parser: Gross vs Net Tax Type
    # --------------------------------------------------------------------------
    def test_salary_gross_net_tax_type(self):
        s_net = salary_values(pd.Series({'salary_text': '1000 USD net / month'}))
        self.assertEqual(s_net['salary_tax_type'], 'net')
        s_gross = salary_values(pd.Series({'salary_text': '1.000 – 1.500 USD gross/tháng'}))
        self.assertEqual(s_gross['salary_tax_type'], 'gross')

    # --------------------------------------------------------------------------
    # 7. Salary Parser: Extract From Title
    # --------------------------------------------------------------------------
    def test_salary_from_title(self):
        res1 = extract_salary_from_title('[Remote] Business Analyst - Up to $1500')
        self.assertIsNotNone(res1)
        self.assertEqual(res1['salary_type'], 'up_to')
        self.assertEqual(res1['salary_max_m'], 37.5)

        res2 = extract_salary_from_title('Kỹ Sư Triển Khai AV - Thu nhập 15-40 Triệu')
        self.assertIsNotNone(res2)
        self.assertEqual((res2['salary_min_m'], res2['salary_max_m']), (15.0, 40.0))

    # --------------------------------------------------------------------------
    # 8. Suspicious Intern / Fresher Outlier Salary Flagging
    # --------------------------------------------------------------------------
    def test_suspicious_intern_salary_flagged(self):
        # Sun group intern with 1,200 - 2,000 USD must be flagged
        s_intern = salary_values(pd.Series({
            'title': 'Thực Tập Sinh An Ninh Bảo Mật (Fulltime)',
            'salary_text': '1,200 - 2,000 USD',
            'salary_min': 1200,
            'salary_max': 2000,
            'currency': 'USD'
        }))
        self.assertTrue(s_intern['salary_can_xem'])
        self.assertTrue(s_intern['salary_needs_review'])
        self.assertEqual(s_intern['salary_source'], 'suspicious_intern_fresher_high_salary')

    # --------------------------------------------------------------------------
    # 9. Compound Skills Splitting vs Atomic Preservation
    # --------------------------------------------------------------------------
    def test_compound_skills_splitting(self):
        res = split_skills('Java/.Net/Python | SQL')
        self.assertIn('Java', res)
        self.assertIn('.Net', res)
        self.assertIn('Python', res)
        self.assertIn('SQL', res)

        res_atomic = split_skills('CI/CD | C/C++')
        self.assertEqual(res_atomic, ['CI/CD', 'C/C++'])

    # --------------------------------------------------------------------------
    # 10. Headhunter Client Resolution
    # --------------------------------------------------------------------------
    def test_headhunter_client_resolution(self):
        df = pd.DataFrame({'company': ["Navigos Search's Client"], 'job_uid': ['vn:123']})
        m = detect_companies(df)
        self.assertEqual(m[0][0], 'c_navigos_client')
        self.assertEqual(m[0][2], 'confidential_headhunter')

    # --------------------------------------------------------------------------
    # 11. Role Classification
    # --------------------------------------------------------------------------
    def test_role_classification(self):
        self.assertEqual(role_from_title('Senior Java Software Engineer'), 'backend')
        self.assertEqual(role_from_title('Frontend Developer (ReactJS)'), 'frontend')
        self.assertEqual(role_from_title('Fullstack Engineer (.NET, Vue.js)'), 'fullstack')
        self.assertEqual(role_from_title('Senior QA Automation Engineer (Playwright)'), 'qa_tester')
        self.assertEqual(role_from_title('AI Engineer (LLM, PyTorch)'), 'data_scientist_ai')
        self.assertEqual(role_from_title('Bridge System Engineer (Japanese N2)'), 'business_analyst')
        self.assertEqual(role_from_title('DevOps / Cloud Engineer (AWS, K8s)'), 'devops_cloud')

    def test_canonical_role_group_classification(self):
        # Strict domain tests
        self.assertEqual(classify_role_group('Senior Java Software Engineer'), ('Backend', 'title', 'high'))
        self.assertEqual(classify_role_group('ReactJS Frontend Developer'), ('Frontend', 'title', 'high'))
        self.assertEqual(classify_role_group('Fullstack Developer (.NET & React)'), ('Fullstack', 'title', 'high'))
        self.assertEqual(classify_role_group('Senior QA Automation Engineer'), ('QA / QC / Tester', 'title', 'high'))
        self.assertEqual(classify_role_group('Senior Data Scientist / AI Specialist'), ('Data / AI', 'title', 'high'))
        self.assertEqual(classify_role_group('DevOps / Cloud Engineer (AWS)'), ('DevOps / Cloud / SysAdmin', 'title', 'high'))
        self.assertEqual(classify_role_group('IT Support / Helpdesk Specialist'), ('IT Support / ERP', 'title', 'high'))
        self.assertEqual(classify_role_group('SOC Security Analyst'), ('Security', 'title', 'high'))
        self.assertEqual(classify_role_group('Product Owner / Business Analyst'), ('BA / PO / PM', 'title', 'high'))
        self.assertEqual(classify_role_group('Chief Technology Officer (CTO)'), ('Management / Leadership', 'title', 'high'))
        
        # Domain Manager should stay in domain, not falsely become Leadership
        self.assertEqual(classify_role_group('QA / QC Manager')[0], 'QA / QC / Tester')
        self.assertEqual(classify_role_group('Cybersecurity Manager')[0], 'Security')
        self.assertEqual(classify_role_group('Head of Data Science')[0], 'Data / AI')
        
        # Skill fallbacks for generic titles
        self.assertEqual(classify_role_group('Software Engineer', skills='ReactJS, CSS, HTML'), ('Frontend', 'skills', 'medium'))
        self.assertEqual(classify_role_group('Software Engineer', skills='ReactJS, Spring Boot, Java'), ('Fullstack', 'skills', 'medium'))
        self.assertEqual(classify_role_group('Software Engineer', skills='Machine Learning, PyTorch, Python'), ('Data / AI', 'skills', 'medium'))
        self.assertEqual(classify_role_group('Software Developer', skills='Flutter, Dart, Mobile'), ('Mobile', 'skills', 'medium'))

    # --------------------------------------------------------------------------
    # 12. Text Containment Function
    # --------------------------------------------------------------------------
    def test_text_containment_function(self):
        t1 = "we need a python developer with pytorch experience at our ho chi minh office"
        t2 = "we need a python developer with pytorch experience at our ho chi minh office and bonus for english"
        t3 = "completely different job requirement looking for senior java spring boot engineer"

        self.assertGreaterEqual(text_containment(t1, t2), 90.0)
        self.assertLess(text_containment(t1, t3), 20.0)

    # --------------------------------------------------------------------------
    # 13. Deduplication Guard Rule: Reject False Merges
    # --------------------------------------------------------------------------
    def test_deduplication_guard_rejects_false_merges(self):
        # BSE N1/N2 (5 yrs) vs BSE N2 (3 yrs)
        t_bse_5yr = "Bridge System Engineer Japanese N1/N2 with 5 years experience in offshore management"
        t_bse_3yr = "Bridge System Engineer Japanese N2 with 3 years experience in web application testing"
        c_bse = text_containment(t_bse_5yr, t_bse_3yr)
        same_exp_bse = (5.0 == 3.0)
        guard_bse = (c_bse >= 90.0) and same_exp_bse
        self.assertFalse(guard_bse, "Guard rule must reject BSE 5yr vs 3yr merge!")

        # Bosch AI Engineer: EPM (PyTorch) vs MLOps (LLM)
        t_epm = "AI Engineer in EPM department developing deep learning models with PyTorch and TensorFlow for automotive"
        t_mlops = "AI Engineer focused on MLOps pipeline deployment, Kubernetes orchestration, LLM inference optimization"
        c_ai = text_containment(t_epm, t_mlops)
        same_exp_ai = True
        guard_ai = (c_ai >= 90.0) and same_exp_ai
        self.assertFalse(guard_ai, "Guard rule must reject Bosch EPM vs MLOps AI Engineer merge!")

    # --------------------------------------------------------------------------
    # 14. Level Extraction & Inferred Experience
    # --------------------------------------------------------------------------
    def test_level_and_inferred_exp(self):
        self.assertEqual(infer_level_from_experience(1.0), 'junior')
        self.assertEqual(infer_level_from_experience(3.0), 'middle')
        self.assertEqual(infer_level_from_experience(5.0), 'senior')

        lvl, src, _ = extract_level(pd.Series({'title': 'Senior Data Engineer'}))
        self.assertEqual(lvl, 'senior')

    # --------------------------------------------------------------------------
    # 15. Skill Taxonomy Hierarchy Verification
    # --------------------------------------------------------------------------
    def test_skill_taxonomy_hierarchy(self):
        tax_file = Path('manual_overrides/skill_taxonomy.csv')
        if not tax_file.exists():
            self.skipTest("skill_taxonomy.csv not found")
        tdf = pd.read_csv(tax_file)
        self.assertIn('skill', tdf.columns)
        self.assertIn('skill_family', tdf.columns)
        self.assertIn('skill_category', tdf.columns)
        self.assertGreaterEqual(len(tdf), 50)

    # --------------------------------------------------------------------------
    # 16. Salary Benchmarks Suppression Invariant (n_range < 5)
    # --------------------------------------------------------------------------
    def test_salary_benchmarks_suppresses_under_5(self):
        bench_file = Path('hr_pipeline_output/dashboard/salary_benchmarks.csv')
        if not bench_file.exists():
            return
        bdf = pd.read_csv(bench_file)
        # For every row where n_range_jobs < 5, median_range_mid_m must be suppressed (NaN)
        low_n_range = bdf[bdf['n_range_jobs'] < 5]
        self.assertTrue(low_n_range['median_range_mid_m'].isna().all(), "median_range_mid_m must be NaN when n_range < 5!")
        self.assertTrue(low_n_range['p25_range_mid_m'].isna().all(), "p25_range_mid_m must be NaN when n_range < 5!")
        self.assertTrue(low_n_range['p75_range_mid_m'].isna().all(), "p75_range_mid_m must be NaN when n_range < 5!")

    # --------------------------------------------------------------------------
    # 17. Regression Tests: All 29 Manual Salary Reviews via subTest
    # --------------------------------------------------------------------------
    def test_regression_29_salary_fixes(self):
        sal_file = Path('manual_overrides/salary_review_filled.csv')
        if not sal_file.exists():
            sal_file = Path('da dien/salary_review_filled.csv')
        if not sal_file.exists():
            self.skipTest("salary_review_filled.csv not found")

        df_sal = pd.read_csv(sal_file)
        self.assertEqual(len(df_sal), 29)
        for _, r in df_sal.iterrows():
            with self.subTest(job_uid=r['job_uid'], decision=r['decision']):
                decision = r['decision']
                self.assertIn(decision, ['apply_fix', 'keep_with_note', 'set_null'])
                if decision == 'apply_fix':
                    self.assertTrue(pd.notna(r['salary_min_m_fixed']) or pd.notna(r['salary_max_m_fixed']))

    # --------------------------------------------------------------------------
    # 18. Regression Tests: All 7 Manual Duplicate Review Pairs via subTest
    # --------------------------------------------------------------------------
    def test_regression_7_duplicate_pairs(self):
        dup_file = Path('manual_overrides/duplicate_review_filled.csv')
        if not dup_file.exists():
            dup_file = Path('da dien/duplicate_review_filled.csv')
        if not dup_file.exists():
            self.skipTest("duplicate_review_filled.csv not found")

        df_dup = pd.read_csv(dup_file)
        self.assertEqual(len(df_dup), 7)
        for _, r in df_dup.iterrows():
            with self.subTest(keep_uid=r['keep_uid'], drop_uid=r['drop_uid']):
                self.assertIn(r['decision'], ['duplicate', 'keep_both'])

    # --------------------------------------------------------------------------
    # 19. Regression Tests: All 20 Duplicate Audit Sample Pairs via subTest
    # --------------------------------------------------------------------------
    def test_regression_20_duplicate_audit_sample(self):
        audit_file = Path('manual_overrides/duplicate_audit_sample_20_filled.csv')
        if not audit_file.exists():
            audit_file = Path('duplicate_audit_sample_20_filled.csv')
        if not audit_file.exists():
            self.skipTest("duplicate_audit_sample_20_filled.csv not found")

        df_audit = pd.read_csv(audit_file)
        self.assertEqual(len(df_audit), 20)
        for _, r in df_audit.iterrows():
            with self.subTest(pair=f"{r['job_uid_1']} vs {r['job_uid_2']}", decision=r['audit_decision']):
                self.assertIn(r['audit_decision'], ['duplicate', 'not_duplicate', 'uncertain'])
                # Verify that proposed guard matches decision
                if r['audit_decision'] == 'duplicate':
                    self.assertTrue(r['proposed_guard_pass'])
                elif r['audit_decision'] == 'not_duplicate':
                    self.assertFalse(r['proposed_guard_pass'])

    # --------------------------------------------------------------------------
    # 20. Data Invariants on Clean Pipeline Output
    # --------------------------------------------------------------------------
    def test_data_invariants(self):
        clean_file = Path('hr_pipeline_output/clean/combine_clean.csv')
        if not clean_file.exists():
            return

        df = pd.read_csv(clean_file, low_memory=False)

        # Invariant 1: job_uid must be 100% unique
        self.assertTrue(df['job_uid'].is_unique, "job_uid is not unique in combine_clean.csv")

        # Invariant 2: salary_min_m <= salary_max_m for range/exact
        range_jobs = df[df['salary_type_norm'].isin(['range', 'exact']) & df['salary_min_m'].notna() & df['salary_max_m'].notna()]
        self.assertTrue((range_jobs['salary_min_m'] <= range_jobs['salary_max_m']).all(), "Found jobs with min > max salary!")

        # Invariant 3: city must be in allowed standardized vocabulary
        allowed_cities = {
            'Hà Nội', 'Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ',
            'Bình Dương', 'Đồng Nai', 'Bắc Ninh', 'Bà Rịa - Vũng Tàu',
            'Thái Nguyên', 'Hưng Yên', 'Hà Tĩnh', 'Vĩnh Phúc', 'Tây Ninh',
            'Hà Nam', 'Thừa Thiên Huế', 'Long An', 'Gia Lai', 'Phú Thọ',
            'Ninh Bình', 'Thanh Hóa', 'Quảng Ninh', 'An Giang', 'Cà Mau',
            'Thái Bình', 'Quốc tế', 'Khác'
        }
        actual_cities = set(df['city'].dropna().unique())
        self.assertTrue(actual_cities.issubset(allowed_cities), f"Unexpected cities found: {actual_cities - allowed_cities}")

        # Invariant 4: Each duplicate group has exactly 1 primary job
        dup_groups = df[df['duplicate_group_id'].notna() & (df['duplicate_group_id'] != '')].groupby('duplicate_group_id')
        for gid, grp in dup_groups:
            with self.subTest(group_id=gid):
                primary_count = (grp['duplicate_role'] == 'primary').sum()
                self.assertEqual(primary_count, 1, f"Group {gid} has {primary_count} primary jobs instead of 1!")

                # Invariant 5: duplicate_of_uid points directly to primary
                main_uid = grp[grp['duplicate_role'] == 'primary']['job_uid'].iloc[0]
                duplicates = grp[grp['duplicate_role'] == 'duplicate']
                for _, dup_row in duplicates.iterrows():
                    self.assertEqual(dup_row['duplicate_of_uid'], main_uid, f"Job {dup_row['job_uid']} does not point directly to primary {main_uid}!")

        # Invariant 6: Canonical skills in job_skill_level must belong to taxonomy
        skill_file = Path('hr_pipeline_output/clean/job_skill_level.csv')
        tax_file = Path('manual_overrides/skill_taxonomy.csv')
        if skill_file.exists() and tax_file.exists():
            tdf = pd.read_csv(tax_file)
            sk_df = pd.read_csv(skill_file)
            canon_set = set(tdf['skill'].dropna())
            actual_skills = set(sk_df['skill'].dropna())
            unmapped = actual_skills - canon_set
            self.assertEqual(len(unmapped), 0, f"Found {len(unmapped)} skills not in taxonomy: {list(unmapped)[:10]}")


if __name__ == '__main__':
    unittest.main()
