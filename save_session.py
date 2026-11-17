"""
Tiện ích hỗ trợ đăng nhập ITviec và lưu phiên (Cookies) vào file auth.json.
Dùng khi phiên đăng nhập hết hạn khiến mức lương hiển thị dạng "Sign in to view salary".

Cách chạy:
    python save_session.py
"""
import os
import sys
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth.json")


def save_session():
    print("=" * 60)
    print("KHỞI TẠO PHIÊN ĐĂNG NHẬP ITVIEC")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://itviec.com/sign_in")

        print("\n1. Trình duyệt đã mở trang đăng nhập ITViec.")
        print("2. Vui lòng đăng nhập tài khoản của bạn trên trình duyệt.")
        print("3. Sau khi đăng nhập thành công vào trang chủ, quay lại đây và nhấn phím ENTER.")
        input("\nNhấn ENTER để tiếp tục...")

        context.storage_state(path=AUTH_FILE)
        print(f"-> Đã lưu phiên đăng nhập thành công vào '{AUTH_FILE}'!")
        browser.close()


if __name__ == "__main__":
    save_session()
