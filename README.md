# Hệ Thống Khảo Sát Giấu Tin Trong Ảnh (Steganography) & Xác Thực Bản Quyền Bằng Blockchain

Dự án nghiên cứu và khảo sát thực nghiệm kỹ thuật giấu tin trong ảnh (Image Steganography) kết hợp với Sổ cái Blockchain bất biến để bảo vệ bản quyền chữ ký số, hợp đồng và tài liệu số quan trọng.

---

## 📌 Các Tính Năng Đạt Chuẩn Nghiên Cứu & Khảo Sát Học Thuật

### 1. Thuật toán Giấu tin Miền không gian (Spatial LSB)
* Hỗ trợ nhúng chuỗi ký tự bản quyền đa ngôn ngữ (UTF-8, tiếng Việt có dấu, ký tự đặc biệt `©`, `®`).
* Tùy biến kênh màu nhúng: Kênh **Xanh lá (G)** (mặc định theo thị giác mắt người), Kênh **Xanh dương (B)**, Kênh **Đỏ (R)**, hoặc Tuần tự **RGB**.
* Tùy biến độ sâu bit: **1-LSB** (chất lượng PSNR cao nhất $> 70\text{ dB}$) hoặc **2-LSB** (gấp đôi sức chứa dung lượng).

### 2. Bộ Chỉ số Đo lường Khoa học (Steganography Quality Metrics)
Tự động tính toán các chỉ số đánh giá sự suy giảm chất lượng ảnh ngay sau khi nhúng tin:
* **PSNR (Peak Signal-to-Noise Ratio)**: Đánh giá tỉ số tín hiệu trên nhiễu (dB).
* **MSE (Mean Squared Error)**: Sai số toàn phương trung bình giữa ảnh gốc và ảnh stego.
* **SSIM (Structural Similarity Index)**: Độ tương đồng cấu trúc hình ảnh $[0, 1]$.
* **Payload & BPP (Bits Per Pixel)**: Tỉ lệ mật độ bit nhúng trên kích thước ảnh.
* **Bản đồ vi sai (Residual / Difference Map x50)**: Phóng đại độ lệch pixel gấp 50 lần để quan sát trực quan vị trí các điểm mang tin.

### 3. Phòng Thí nghiệm Khảo sát Độ bền vững & Tấn công (Robustness Benchmark Lab)
Mô phỏng 5 kịch bản xử lý ảnh / tấn công thực tế để làm bảng số liệu khảo sát:
1. **Nén JPEG chất lượng 85%** (Nén mất mát dữ liệu thường gặp khi upload mạng xã hội).
2. **Nén JPEG chất lượng 60%** (Nén mạnh).
3. **Thay đổi độ sáng (+10% Brightness)**.
4. **Lọc mờ Gauss (Gaussian Blur r=1.0)**.
5. **Nhiễu ngẫu nhiên kênh truyền (Noise Injection $\pm 2$)**.
* Xuất bảng đo lường **Tỉ lệ lỗi bit (Bit Error Rate - BER %)**, tỉ lệ sống sót của watermark và kiểm chứng năng lực phát hiện can thiệp của Blockchain.

### 4. Sổ cái Bản quyền Phân tán (Blockchain Ledger Explorer)
* Lưu trữ bất biến mã băm toàn vẹn `SHA-256(Ảnh)` và `SHA-256(Watermark)`.
* Sinh mã giao dịch `tx_hash`, mốc thời gian UTC và thông tin tác giả.
* Trang tra cứu, tìm kiếm và kiểm tra nhanh các khối (blocks) đã đăng ký.

### 5. Trang Báo cáo Cơ sở Lý thuyết (Theory Docs)
* Tổng hợp định nghĩa, công thức toán học (MSE, PSNR, SSIM, BER, HVS).
* Phân tích điểm yếu của LSB và giải pháp bảo vệ 100% bằng Blockchain.

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### Yêu cầu môi trường
* Python 3.9+ (Đã kiểm thử mượt mà trên Python 3.10 - 3.13)
* Các thư viện: `Flask`, `Pillow`, `numpy`, `scikit-image`, `opencv-python-headless`

### Cài đặt thư viện
```bash
pip install -r requirements.txt
pip install scikit-image
```

### Khởi chạy ứng dụng
```bash
python app.py
```
Mở trình duyệt truy cập: **`http://127.0.0.1:5000`**

---

## 📂 Cấu Trúc Mã Nguồn

```text
├── app.py                 # Máy chủ web Flask và các API điều hướng
├── watermark.py           # Thuật toán giấu tin LSB tùy biến kênh & độ sâu bit
├── metrics.py             # Bộ công cụ tính toán PSNR, MSE, SSIM và mô phỏng tấn công
├── blockchain_mock.py     # Giả lập sổ cái Blockchain lưu trữ giao dịch SHA-256
├── ledger.json            # Cơ sở dữ liệu sổ cái phân tán
├── static/
│   ├── css/style.css      # Tệp định dạng giao diện
│   └── uploads/           # Thư mục lưu trữ ảnh đã nhúng watermark
└── templates/
    ├── base.html          # Layout nền giao diện và thanh điều hướng Tabs
    ├── index.html         # Trang chủ: Nhúng tin & Xác thực bản quyền
    ├── result_embed.html  # Báo cáo kết quả nhúng & đo lường chất lượng ảnh
    ├── result_verify.html # Báo cáo kết quả đối soát toàn vẹn Blockchain
    ├── benchmark.html     # Phòng thí nghiệm thử nghiệm tấn công (Attack Lab)
    ├── ledger.html        # Khám phá Sổ cái Blockchain (Ledger Explorer)
    └── theory.html        # Tổng hợp cơ sở lý thuyết khoa học
```
