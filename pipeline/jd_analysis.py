"""Conservative, evidence-backed extraction from recruitment requirements and descriptions."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

IMP_WEIGHT = {'required': 1.0, 'preferred': 0.5, 'duty': 0.3, 'listed_only': 0.2}
PROF_SCORE = {'advanced': 3, 'intermediate': 2, 'basic': 1, 'unspecified': 2}

PREFERRED = re.compile(
    r'\b(?:preferred|preferably|nice to have|good to have|bonus|plus|advantage|optional|desirable|'
    r'uu tien|loi the|diem cong|khuyen khich)\b', re.I
)
ADVANCED = re.compile(
    r'\b(?:advanced|expert|expertise|proficient|proficiency|mastery|master|strong|deep knowledge|'
    r'in.depth|excellent|fluent|thanh thao|chuyen sau|nam vung|hieu biet sau|xuat sac)\b', re.I
)
INTERMEDIATE = re.compile(
    r'\b(?:intermediate|hands.on|solid|good command|good knowledge|experience (?:in|with)|'
    r'experienced|working knowledge|competent|co kinh nghiem|kien thuc tot|am hieu|vung chac|kha tot)\b', re.I
)
BASIC = re.compile(
    r'\b(?:basic|fundamental|fundamentals|familiar with|familiarity|beginner|entry.level|'
    r'co ban|nen tang|lam quen|biet ve)\b', re.I
)
NEGATIVE = re.compile(
    r'\b(?:not required|no experience|required to learn|willing to learn|opportunity to learn|'
    r'khong yeu cau|khong bat buoc|san sang hoc|duoc dao tao)\b', re.I
)
EXPERIENCE = re.compile(
    r'(?<!\w)(\d+(?:[.,]\d+)?)\s*(?:-|–|—|to|den)\s*(\d+(?:[.,]\d+)?)\s*(years?|yrs?|nam|months?|mos?|thang)\b|'
    r'(?<!\w)(\d+(?:[.,]\d+)?)\s*\+?\s*(years?|yrs?|nam|months?|mos?|thang)\b', re.I
)
EXP_CONTEXT = re.compile(
    r'\b(?:experience|experienced|kinh nghiem|exp\.?|working years|professional years)\b', re.I
)

# Cue cấp bậc trong TIÊU ĐỀ; cue xuất hiện ĐẦU TIÊN thắng ('Mid/Senior' -> middle, 'Senior/Lead' -> senior).
LEVEL_CUES = [
    ('intern', r'intern|internship|trainee|thuc tap|tap su'),
    ('fresher', r'fresher|freshers|graduate|moi tot nghiep|moi ra truong|entry level'),
    ('junior', r'junior|jr'),
    ('middle', r'middle|mid|mid level|intermediate'),
    ('senior', r'senior|sr|snr|principal|staff|cao cap'),
    ('lead', r'lead|leader|team lead|tech lead|technical lead|truong nhom|giam sat|supervisor'),
    ('manager', r'head of|head|deputy head|truong phong|pho phong|department manager|engineering manager|it manager'),
    ('director', r'director|giam doc|cto|cio|ceo|coo|cdo|ciso|vp|vice president|truong khoi|chief'),
]
ROLE_MANAGER = re.compile(
    r'(?:project|product|program|programme|delivery|account|release|service|portfolio|change|'
    r'sales|marketing|quality|test|qa|qc|it|hr|talent|community|security|operations|business|'
    r'engineering|solution|technical)\s+manager'
)


def as_text(value):
    return str(value) if value is not None and str(value).lower() not in {'nan', 'none'} else ''


def plain(text):
    s = unicodedata.normalize('NFKD', text.lower().replace('đ', 'd'))
    return ''.join(c for c in s if not unicodedata.combining(c))


def segments(text):
    """Split bullet lines and sentences; preserve whole evidence snippets."""
    text = re.sub(r'<[^>]*>', ' ', as_text(text))
    bits = re.split(r'[\r\n•●;]+|(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])', text)
    return [re.sub(r'\s+', ' ', s).strip(' -\t') for s in bits if len(s.strip()) >= 3]


def experience_from_text(text):
    candidates = []
    for line in segments(text):
        normalized = plain(line)
        if NEGATIVE.search(normalized):
            continue
        for match in EXPERIENCE.finditer(normalized):
            a, b, unit_range, single, unit_single = match.groups()
            unit = unit_range or unit_single
            first = float((a or single).replace(',', '.'))
            second = float(b.replace(',', '.')) if b else None
            if unit.startswith(('month', 'mo', 'thang')):
                first /= 12
                second = second / 12 if second is not None else None
            if first > 30 or (second is not None and (second > 30 or second < first)):
                continue
            candidates.append((round(first, 2), round(second, 2) if second is not None else None, line[:350]))
    return candidates


def extract_experience(row):
    raw = as_text(row.get('experience_raw'))
    req = as_text(row.get('requirement'))
    desc = as_text(row.get('description'))
    for src, value in [('goc_experience', raw), ('requirement', req), ('description', desc)]:
        found = experience_from_text(value)
        if found:
            lowest, highest, evidence = max(found, key=lambda t: t[0])
            return {'exp_min_years': lowest, 'exp_max_years': highest,
                    'exp_source': src, 'exp_nguon': src, 'exp_evidence': evidence,
                    'exp_can_xem': len({a for a, _, _ in found}) > 1,
                    'exp_needs_review': len({a for a, _, _ in found}) > 1}
        if src == 'goc_experience' and re.search(r'khong yeu cau|no experience|fresher', plain(value), re.I):
            return {'exp_min_years': 0, 'exp_max_years': None,
                    'exp_source': src, 'exp_nguon': src, 'exp_evidence': value[:350],
                    'exp_can_xem': False, 'exp_needs_review': False}
    return {'exp_min_years': None, 'exp_max_years': None,
            'exp_source': 'khong_xac_dinh', 'exp_nguon': 'khong_xac_dinh',
            'exp_evidence': '', 'exp_can_xem': False, 'exp_needs_review': False}


def extract_level(row, exp_min=None):
    """level_norm CHỈ dựa vào tiêu đề (cue đầu tiên). Cấp gốc chỉ dùng cho intern/fresher/director.
    exp_min giữ lại để tương thích chữ ký hàm; suy luận theo số năm ở hàm infer_level_from_experience (cột riêng).
    """
    title = ' ' + re.sub(r'[^a-z0-9]+', ' ', plain(as_text(row.get('title')))) + ' '
    title = re.sub(r' tro ly [a-z ]*?(giam doc|tgd) ', ' ', title)
    if re.search(r' (?:assistant|tro ly|tai xe|driver|secretary) ', title):
        title = re.sub(r' (?:director|giam doc|ceo|cto|cio|head|manager) ', ' ', title)
    best = None
    for level, pat in LEVEL_CUES:
        m = re.search(r'(?<= )(?:' + pat + r')(?= )', title)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), level)
    if best:
        return best[1], 'title', False
    if re.search(r' (?:manager|managers|quan ly) ', title) and not ROLE_MANAGER.search(title) \
            and not re.search(r'quan ly (?:he thong|du an|san pham|chat luong|cong nghe|ha tang|rui ro)', title):
        return 'manager', 'title', False
    raw_level = plain(as_text(row.get('level')))
    if re.search(r'intern|thuc tap|sinh vien', raw_level):
        return 'intern', 'level', False
    if re.search(r'fresher|moi tot nghiep', raw_level):
        return 'fresher', 'level', False
    if re.search(r'giam doc|director', raw_level):
        return 'director', 'level', False
    return 'unknown', 'khong_xac_dinh', False


def infer_level_from_experience(exp_min):
    """Gợi ý cấp bậc theo số năm kinh nghiệm tối thiểu. Lưu ở cột riêng level_inferred_exp."""
    if exp_min is None:
        return ''
    return 'junior' if exp_min <= 1 else 'middle' if exp_min < 5 else 'senior'


def skill_variants(raw, canonical, extra=()):
    """Use literal tag and safe descriptive expansions; omit generic ambiguous words."""
    variants = {as_text(raw).strip()}
    if canonical:
        variants.add(canonical)
    safe = {
        'Business Analysis (BA)': ['business analysis', 'business analyst', 'phân tích nghiệp vụ'],
        'Artificial Intelligence (AI)': ['artificial intelligence', 'generative ai'],
        'JavaScript / TypeScript': ['javascript', 'typescript'],
        'Agile & Scrum': ['agile', 'scrum'],
        'Containers & Orchestration': ['docker', 'kubernetes', 'k8s'],
        'Frontend Development': ['frontend', 'front-end', 'reactjs', 'react.js'],
        'Backend Development': ['backend', 'back-end', 'nodejs', 'node.js'],
        'Software Testing': ['testing', 'test engineer', 'manual tester'],
        'Test Automation': ['automation testing', 'automated testing'],
        'Cloud Computing': ['cloud computing'],
    }
    variants.update(safe.get(canonical, []))
    variants.update(extra or [])
    unsafe = {'ai', 'ba', 'qa', 'it', 'go', 'c', 'r', 'product', 'manager', 'mobile', 'cloud', 'security', 'database', 'testing', 'leadership', 'dev'}
    return [v for v in variants if len(v) >= 2 and plain(v) not in unsafe]


@lru_cache(maxsize=4096)
def _evidence_pattern(variants):
    escaped = [re.escape(v) for v in variants]
    return re.compile(r'(?<![\w])(?:' + '|'.join(sorted(escaped, key=len, reverse=True)) + r')(?![\w])', re.I)


def find_evidence(text, variants):
    if not variants:
        return []
    pattern = _evidence_pattern(tuple(sorted(variants)))
    return [line for line in segments(text) if pattern.search(line)]


def preferred_in_scope(line, variants):
    """Cue 'ưu tiên / plus' chỉ áp cho MỆNH ĐỀ chứa skill (tách bởi , ; ( ) )."""
    if not variants:
        return bool(PREFERRED.search(plain(line)))
    rx = re.compile(r'(?<![\w])(?:' + '|'.join(sorted(map(re.escape, variants), key=len, reverse=True)) + r')(?![\w])', re.I)
    m = rx.search(line)
    if not m:
        return bool(PREFERRED.search(plain(line)))
    left = max(line.rfind(ch, 0, m.start()) for ch in ',;()')
    rights = [i for i in (line.find(ch, m.end()) for ch in ',;()') if i >= 0]
    clause = line[left + 1:(min(rights) if rights else len(line))]
    return bool(PREFERRED.search(plain(clause)))


def classify_skill(row, raw, canonical, extra=()):
    variants = skill_variants(raw, canonical, extra)
    req_evs = find_evidence(row.get('requirement'), variants)
    duty_evs = find_evidence(row.get('description'), variants)
    if req_evs:
        positive = [s for s in req_evs if not NEGATIVE.search(plain(s))]
        if positive:
            preferred = [s for s in positive if preferred_in_scope(s, variants)]
            required = [s for s in positive if s not in preferred]
            importance = 'required' if required else 'preferred'
            evidence = (required or preferred)[0]
            source = 'requirement'
        else:
            importance, evidence, source = 'listed_only', req_evs[0], 'requirement_negative'
    elif duty_evs:
        importance, evidence, source = 'duty', duty_evs[0], 'description'
    else:
        importance, evidence, source = 'listed_only', '', 'tag_only'

    prof = 'unspecified'
    prof_source = 'none'
    years_min = None
    if importance in {'required', 'preferred'}:
        clause = plain(evidence)
        if ADVANCED.search(clause):
            prof, prof_source = 'advanced', 'cue'
        elif BASIC.search(clause):
            prof, prof_source = 'basic', 'cue'
        elif INTERMEDIATE.search(clause):
            prof, prof_source = 'intermediate', 'cue'
        near = experience_from_text(evidence)
        if near:
            years_min = near[0][0]
    needs_review = (importance == 'listed_only' and bool(req_evs)) or (
        len(req_evs) > 1 and any(preferred_in_scope(s, variants) for s in req_evs) and any(not preferred_in_scope(s, variants) for s in req_evs)
    )
    return {'importance': importance, 'proficiency': prof, 'prof_source': prof_source,
            'years_min': years_min, 'source': source, 'evidence': evidence[:600],
            'imp_weight': IMP_WEIGHT[importance], 'prof_score': PROF_SCORE[prof],
            'match_weight': round(IMP_WEIGHT[importance] * PROF_SCORE[prof], 2),
            'skill_can_xem': needs_review, 'skill_needs_review': needs_review}
