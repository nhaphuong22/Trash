# 🗑️ AI Waste Sorter System (Jetson Nano + YOLO)

Dự án sử dụng Trí tuệ nhân tạo (YOLO) để nhận diện và phân loại rác thải (Kim loại & Nhựa) trong thời gian thực, kết hợp với cánh tay Servo để thực hiện hành động phân loại vật lý trên phần cứng NVIDIA Jetson.

---

## 🚀 Tính năng chính
* **AI Real-time Detection:** Sử dụng YOLOv8 (tối ưu hóa TensorRT `.engine`) để nhận diện rác với độ trễ thấp.
* **Hardware Control:** Điều khiển 2 động cơ Servo để phân loại rác vào các ngăn tương ứng thông qua thư viện Jetson.GPIO.
* **Web Dashboard:** Livestream quá trình nhận diện và thống kê số lượng qua giao thức HTTP (Flask).
* **Stability Logic:** Thuật toán lọc nhiễu dựa trên lịch sử khung hình giúp hệ thống hoạt động chính xác, tránh gạt nhầm.

---

## 🛠️ Luồng vận hành (Workflow)



### 1. Khởi tạo & Thiết lập (Initialization)
Hệ thống bắt đầu bằng việc cấu hình môi trường tính toán và phần cứng:
* **Tối ưu hóa:** Cấu hình `OpenBLAS` và `libgomp` để tối đa hiệu suất tính toán trên kiến trúc ARM (kiến trúc ở trên Jetson).
* **GPIO:** Thiết lập chân **32 (Metal)** và **33 (Plastic)** theo chế độ BOARD.
* **Model:** Ưu tiên tải mô hình đã được build qua TensorRT (`.engine`) để chạy cực nhanh, nếu không có sẽ tự động chuyển sang mô hình PyTorch (`.pt`).
* **Multi-threading:** Khởi chạy Flask server tại cổng `5000` trên một luồng riêng để không làm gián đoạn luồng xử lý AI.

### 2. Luồng xử lý hình ảnh chính (Main Loop)
Quá trình xử lý diễn ra lặp hồi qua 3 bước:
* **Bước A - Tiền xử lý:** Camera đọc khung hình, vẽ Dashboard thống kê và xác định vùng **ROI (Region of Interest)**. AI chỉ tập trung quét trong vùng từ `(150, 100)` đến `(490, 380)` để tiết kiệm tài nguyên.
* **Bước B - Nhận diện:** Sử dụng `FRAME_SKIP=2` để giảm tải cho GPU. Hệ thống tìm vật thể có diện tích lớn nhất trong vùng ROI và có độ tự tin (Confidence) trên 50%.
* **Bước C - Thuật toán ổn định:** Kết quả được đưa vào một hàng đợi (Queue). Cánh tay cơ khí chỉ kích hoạt khi một loại rác (METAL hoặc PLASTIC) xuất hiện ổn định ít nhất **3 lần** trong các khung hình gần nhất.

### 3. Điều khiển Servo (Actuation)
Khi rác được xác nhận ổn định:
* **Metal (Chân 32):** Sử dụng xung PWM phần cứng, gạt một góc 135° rồi quay lại 90°.
* **Plastic (Chân 33):** Sử dụng xung PWM mềm, gạt một góc 45° rồi quay lại 90°.
* **Cooldown:** Hệ thống áp dụng khoảng nghỉ 2.5 giây giữa các lần gạt để cơ cấu cơ khí có thời gian hồi vị.



---

## 📊 Thông số kỹ thuật
| Thông số | Giá trị |
| :--- | :--- |
| **Model Size** | 320x320 px |
| **Vùng ROI** | 150x100 đến 490x380 |
| **Ngưỡng tự tin (Conf)** | 0.50 |
| **Thời gian nghỉ (Cooldown)** | 2.5 giây |
| **Cổng Web Stream** | 5000 |

---

## 💻 Cài đặt & Sử dụng

### Yêu cầu hệ thống
* Thiết bị NVIDIA Jetson (Nano, Xavier, hoặc Orin).
* Thư viện: `opencv-python`, `torch`, `ultralytics`, `Jetson.GPIO`, `flask`.

### Cách chạy
1.  Kết nối Camera USB và 2 Servo vào chân GPIO 32 và 33.
2.  Mở terminal và chạy lệnh:
    ```bash
    python3 main.py
    ```
3.  Xem livestream tại địa chỉ: `http://localhost:5000/video_feed` (thay localhost bằng IP của Jetson nếu xem từ máy khác).

---

## 🛡️ Quản lý tài nguyên & An toàn
* **Memory Management:** Tự động giải phóng bộ nhớ đệm CUDA và rác (Garbage Collection) sau mỗi 100 khung hình để tránh treo máy.
* **Thread Safety:** Sử dụng `threading.Lock()` để đảm bảo luồng livestream không truy cập dữ liệu cùng lúc với luồng xử lý AI.
* **Cleanup:** Khi dừng chương trình (`Ctrl+C`), hệ thống tự động tắt xung PWM và giải phóng các chân GPIO để bảo vệ linh kiện.

---
*Developed for Smart Waste Management Systems.*