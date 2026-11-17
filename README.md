# Vietnam IT Job Market

Hệ thống thu thập, theo dõi vòng đời và phân tích dữ liệu thị trường việc làm ngành Công nghệ Thông tin tại Việt Nam (VietnamWorks, ITviec).

---

## 📁 Cấu trúc dự án

```text
vietnam-it-job-market/
├── crawlers/
│   ├── vietnamworks/        # Module crawl & tracking VietnamWorks
│   │   ├── config.py        # Cấu hình API, headers, tỷ giá, đường dẫn
│   │   ├── spider.py        # Thu thập Search API & chi tiết tin
│   │   ├── parsers.py       # Bóc tách metadata, quy đổi lương VND, flight Next.js
│   │   ├── tracker.py       # Theo dõi vòng đời tin (active/gone, days_alive)
│   │   └── pipeline.py      # Quy trình crawl hoàn chỉnh
│   └── itviec/              # Module crawl ITviec (Playwright)
├── data/                    # Thư mục dữ liệu (tự động tạo khi chạy)
│   ├── daily/               # Snapshot dữ liệu theo từng ngày crawl
│   └── master/              # File tổng hợp toàn bộ lịch sử tin tuyển dụng
├── daily_crawl.py           # Script chạy crawl hàng ngày qua dòng lệnh
└── README.md
```

---

## 🚀 Cài đặt

Yêu cầu Python 3.10 trở lên. Cài đặt các thư viện cần thiết:

```bash
pip install httpx pandas
```

*(Nếu sử dụng thêm crawler ITviec, cài thêm `playwright` và chạy `playwright install chromium`)*

---

## ⚡ Hướng dẫn chạy Crawler

### 1. Chạy crawl hàng ngày (VietnamWorks)
Chỉ cần chạy lệnh sau từ thư mục gốc dự án:

```bash
python daily_crawl.py
```
Hoặc gọi trực tiếp module:
```bash
python -m crawlers.vietnamworks.pipeline
```

### 2. Các tùy chọn hữu ích

| Tham số | Ý nghĩa | Mặc định |
| :--- | :--- | :--- |
| `--pages N` | Giới hạn số trang cần cào | `30` (~1.500 tin) |
| `--enrich-views` | Cào thêm lượt xem/hồ sơ ứng tuyển từ trang chi tiết | Tắt |
| `--date YYYY-MM-DD` | Chỉ định ngày crawl cụ thể | Hôm nay |
| `--save-raw` | Lưu thêm bản sao JSON thô vào `data/raw/` | Tắt |
| `--partial` | Chế độ crawl dở dang (không đánh dấu `gone` cho tin cũ) | Tắt |

**Ví dụ:**
```bash
# Cào nhanh 10 trang đầu
python daily_crawl.py --pages 10

# Cào đầy đủ kèm lượt xem và ứng tuyển
python daily_crawl.py --enrich-views
```

---

## 📊 Dữ liệu đầu ra

Sau mỗi lần chạy, dữ liệu được chuẩn hóa và lưu tại:

- **`data/daily/vietnamworks_YYYY-MM-DD.csv`**: Danh sách toàn bộ tin tuyển dụng quan sát được trong ngày, kèm cờ `is_new` (1 nếu là tin mới phát hiện).
- **`data/master/vietnamworks_jobs.csv`**: File Master duy nhất lưu lịch sử tất cả các tin:
  - `status`: Trạng thái tin (`active` = đang mở, `gone` = đã gỡ/hết hạn).
  - `days_alive`, `observed_days_alive`: Số ngày tin tồn tại thực tế trên thị trường.
  - `days_to_expire`: Số ngày còn lại trước hạn nộp hồ sơ.
  - `end_reason`: `expired` (hết hạn tự nhiên) hoặc `removed_early` (nhà tuyển dụng đóng sớm).
  - `salary_min_mvnd_month`, `salary_max_mvnd_month`: Mức lương chuẩn hóa về triệu VND/tháng.
