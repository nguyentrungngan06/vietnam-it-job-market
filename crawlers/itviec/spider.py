"""
Module Spider thu thập dữ liệu bằng Playwright (Step 1: Quét Card & Step 2: Cào Chi Tiết JD).
"""
import os
import re
import time
from datetime import date
import pandas as pd
from playwright.sync_api import BrowserContext

from .config import AUTH_FILE, CHECKPOINT_FILE, SALARY_COLS, KNOWN_CITIES
from .parsers import (
    ascii_lower,
    make_job_key,
    generate_numeric_job_id,
    is_category_url,
    parse_salary_fields,
    clean_company_size,
    infer_level,
    infer_work_mode,
    infer_company_type,
    infer_posted_date,
    parse_job_skills,
    split_company_address,
    city_from_address,
    extract_page_metadata,
    header_lines,
    extract_company,
)


def create_browser_context(playwright_instance, headless=True, auth_file=AUTH_FILE) -> BrowserContext:
    """Khởi tạo Browser và Context tối ưu tốc độ, áp dụng auth.json nếu có."""
    browser = playwright_instance.chromium.launch(headless=headless)
    storage_state = auth_file if (auth_file and os.path.exists(auth_file)) else None
    if storage_state:
        print(f"  -> Đã nạp phiên đăng nhập từ: {storage_state}")
    else:
        print("  -> [CẢNH BÁO] Không tìm thấy auth.json, chạy ở chế độ khách (không xem được mức lương)")

    context = browser.new_context(
        storage_state=storage_state,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    )
    return browser, context


def crawl_job_cards(page, max_pages=40):
    """
    [BƯỚC 1] Quét danh sách bài tuyển dụng từ các trang tìm kiếm (page 1..max_pages).
    Trích xuất trực tiếp card metadata và URL.
    """
    today_iso = date.today().isoformat()
    cards_data = []
    seen_keys = set()

    # Chặn tài nguyên tĩnh không cần thiết để tăng tốc
    page.route("**/*.{png,jpg,jpeg,webp,svg,gif,woff,woff2}", lambda route: route.abort())

    print(f"\n[BƯỚC 1] Thu thập danh sách bài tuyển dụng (Tối đa {max_pages} trang)...")

    for page_num in range(1, max_pages + 1):
        url = f"https://itviec.com/it-jobs?page={page_num}"
        print(f"  - Đang quét trang {page_num}: {url}", end=" ")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            try:
                page.wait_for_selector("div.job-card, div.item-card", timeout=8000)
            except Exception:
                pass
        except Exception as e:
            print(f"\n  -> Dừng quét do lỗi tải trang: {e}")
            break

        time.sleep(0.4)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.4)

        raw_cards = page.evaluate(
            """() => {
            const cards = Array.from(document.querySelectorAll('div.job-card, div.item-card'));
            return cards.map(card => {
                const titleLink = card.querySelector("h3 a[href*='/it-jobs/'], a[data-search--job-selection-target='jobTitle'], a[href*='/it-jobs/']");
                const h3 = card.querySelector("h3[data-url]");
                let href = titleLink ? (titleLink.getAttribute('href') || '') : '';
                if ((!href || href === 'null') && h3) {
                    href = h3.getAttribute('data-url') || '';
                }
                const title = titleLink ? titleLink.innerText.trim() : (h3 ? h3.innerText.trim() : '');

                const compLink = card.querySelector("a[href*='/companies/']:not(.logo-employer-card):not(.job-card-logo)") || card.querySelector("a[href*='/companies/']");
                const compHref = compLink ? (compLink.getAttribute('href') || '') : '';
                const compName = compLink ? compLink.innerText.trim() : '';

                const salEl = card.querySelector("div.salary span, div.salary");
                const salText = salEl ? salEl.innerText.trim() : '';

                const cardText = card.innerText || '';
                const skillLinks = Array.from(card.querySelectorAll("a[href*='click_source=Skill+tag']")).map(a => a.innerText.trim()).filter(Boolean);

                return { href, title, compHref, compName, salText, cardText, skills: skillLinks };
            });
        }"""
        )

        new_in_page = 0
        for item in raw_cards:
            href = item.get("href", "").strip()
            title = item.get("title", "").strip()
            if not href or "/it-jobs/" not in href or "page=" in href or len(title) < 3:
                continue
            if any(tag in href for tag in ["click_source=", "location/", "skill/"]):
                continue
            if is_category_url(href, title):
                continue

            full_url = f"https://itviec.com{href}" if href.startswith("/") else href
            jkey = make_job_key(full_url)
            if not jkey or jkey in seen_keys:
                continue

            seen_keys.add(jkey)

            comp_href = item.get("compHref", "")
            m_slug = re.search(r"/companies/([^/?#]+)", comp_href)
            comp_slug = m_slug.group(1) if m_slug else None

            comp_name = item.get("compName", "").strip() or "N/A"
            if comp_name == "Urgent":
                continue

            ctext = item.get("cardText", "")
            m_post = re.search(r"(Posted\s+[^\n]+?ago|Đăng\s+[^\n]+?trước)", ctext, re.I)
            posted_text = m_post.group(1).strip() if m_post else None
            posted_date = infer_posted_date(today_iso, posted_text)

            m_wm = re.search(r"\b(At office|Hybrid|Remote|Tại văn phòng|Linh hoạt|Từ xa)\b", ctext, re.I)
            raw_wm = m_wm.group(1).strip() if m_wm else None
            work_mode = infer_work_mode(title, raw_work_mode=raw_wm)

            city = "N/A"
            low_ctext = ascii_lower(ctext)
            for k_city, c_name in KNOWN_CITIES:
                if k_city in low_ctext:
                    city = c_name
                    break

            skills_list = item.get("skills") or []
            skills_str = " | ".join(dict.fromkeys(skills_list)) if skills_list else "N/A"

            sal_info = parse_salary_fields(sal_text=item.get("salText", ""))

            cards_data.append({
                "job_key": jkey,
                "job_id": generate_numeric_job_id(jkey),
                "url": full_url,
                "title": title,
                "company": comp_name,
                "company_slug": comp_slug,
                "city": city,
                "work_mode": work_mode,
                "posted_text": posted_text,
                "posted_date": posted_date,
                "skills": skills_str,
                "salary_visible": sal_info["salary_visible"],
                "salary_min": sal_info["salary_min"],
                "salary_max": sal_info["salary_max"],
                "currency": sal_info["currency"],
                "salary_text": sal_info["salary_text"],
                "salary_type": sal_info["salary_type"],
                "salary_from_text": sal_info["salary_from_text"],
            })
            new_in_page += 1

        print(f"-> Thu được {new_in_page} bài (Tổng: {len(cards_data)})")
        if new_in_page == 0 and page_num > 1:
            print(f"  -> Đã tới trang cuối cùng ({page_num}).")
            break

    return cards_data


def crawl_job_details(page, cards_data, checkpoint_file=CHECKPOINT_FILE):
    """
    [BƯỚC 2] Truy cập từng trang chi tiết công việc để cào:
    - JD (Mô tả công việc) & Requirement (Yêu cầu công việc)
    - Skills chính xác từ DOM
    - Quy mô công ty, loại hình công ty, cấp bậc (level)
    """
    today_iso = date.today().isoformat()
    checkpoint_done = {}

    if os.path.exists(checkpoint_file):
        try:
            df_cp = pd.read_csv(checkpoint_file, dtype=str)
            for _, r in df_cp.iterrows():
                checkpoint_done[r["job_key"]] = r.to_dict()
            print(f"  -> Tìm thấy checkpoint với {len(checkpoint_done)} bài đã cào trước đó.")
        except Exception:
            pass

    full_jobs = []
    print(f"\n[BƯỚC 2] Cào chi tiết JD & Requirements cho {len(cards_data)} bài đăng...")

    for idx, card in enumerate(cards_data, start=1):
        jkey = card["job_key"]
        if jkey in checkpoint_done:
            full_jobs.append(checkpoint_done[jkey])
            continue

        url = card["url"]
        print(f"  [{idx}/{len(cards_data)}] {card['title'][:38]} | {card['company'][:22]}", end=" ... ")

        row = dict(card)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=18000)
            try:
                page.wait_for_selector("h1", timeout=6000)
            except Exception:
                pass
            time.sleep(0.3)

            body_text = page.inner_text("body")
            if "Oops! The job you're looking for doesn't exist" in body_text:
                print("tin đã đóng")
                continue

            title_elem = page.locator("h1").first
            title = title_elem.inner_text().strip() if title_elem.is_visible() else card["title"]

            # Lấy địa chỉ và công ty
            text_name, address = split_company_address(header_lines(body_text, title))
            company, company_slug = extract_company(page, text_name, url)
            if company != "N/A" and company != "Urgent":
                row["company"] = company
            if company_slug:
                row["company_slug"] = company_slug

            city_detail = city_from_address(address)
            if city_detail != "N/A":
                row["city"] = city_detail

            # Lương trực tiếp từ khối lương của trang chi tiết
            salary_elem = page.locator("div.salary span, .job-details__salary, .salary-text").first
            raw_sal_detail = salary_elem.inner_text().strip() if salary_elem.is_visible() else None
            if raw_sal_detail:
                sal_detail = parse_salary_fields(sal_text=raw_sal_detail)
                if sal_detail["salary_type"] != "missing":
                    for k_sal in SALARY_COLS:
                        row[k_sal] = sal_detail[k_sal]

            # Bóc tách skills chính xác từ DOM HTML
            html_content = page.content()
            skills_detail = parse_job_skills(html_content)
            if skills_detail != "N/A":
                row["skills"] = skills_detail

            # Description & Requirement
            desc_elem = page.locator("div.job-description, div:has-text('Job description')").last
            req_elem = page.locator("div.job-requirements, div:has-text('Your skills and experience')").last
            description = desc_elem.inner_text().strip() if desc_elem.is_visible() else "N/A"
            requirement = req_elem.inner_text().strip() if req_elem.is_visible() else "N/A"

            meta = extract_page_metadata(body_text, title)
            level = infer_level(title, requirement, description)
            work_mode = infer_work_mode(title, description, requirement, meta["raw_work_mode"] or card["work_mode"])
            company_type = infer_company_type(row["company"], description, requirement, meta["raw_company_type"])
            company_size = clean_company_size(meta["raw_company_size"])

            row["description"] = description
            row["requirement"] = requirement
            row["level"] = level
            row["work_mode"] = work_mode
            row["company_type"] = company_type
            row["company_size"] = company_size
            row["company_size_range"] = meta["raw_company_size"] if company_size != "unknown" else "unknown"
            row["posted_date"] = infer_posted_date(today_iso, meta["raw_posted_text"] or card["posted_text"])
            row["site"] = "itviec"
            row["first_seen"] = today_iso
            row["last_seen"] = today_iso
            row["days_active"] = 1
            row["is_active"] = True

            print(f"OK ({level} | {work_mode})")
        except Exception as e:
            print(f"Lỗi tải trang: {str(e)[:30]}")
            row["description"] = "N/A"
            row["requirement"] = "N/A"
            row["level"] = infer_level(card["title"])
            row["company_type"] = infer_company_type(card["company"])
            row["company_size"] = "unknown"
            row["company_size_range"] = "unknown"
            row["site"] = "itviec"
            row["first_seen"] = today_iso
            row["last_seen"] = today_iso
            row["days_active"] = 1
            row["is_active"] = True

        full_jobs.append(row)

        # Lưu checkpoint sau mỗi 20 bài
        if idx % 20 == 0:
            pd.DataFrame(full_jobs).to_csv(checkpoint_file, index=False, encoding="utf-8-sig")

    if os.path.exists(checkpoint_file):
        try:
            os.remove(checkpoint_file)
        except OSError:
            pass

    return full_jobs
