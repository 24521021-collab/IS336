# Đồ án IS336 - Hệ thống Hoạch định Nguồn lực Doanh nghiệp (Odoo 18.0)

Dự án sử dụng **Odoo 18.0** chạy trên **Docker** và kết nối chung tới cơ sở dữ liệu **PostgreSQL trên Cloud (Neon)** để toàn bộ thành viên trong nhóm có thể làm việc và đồng bộ dữ liệu theo thời gian thực.

---

## ❓ Câu hỏi thường gặp: Có cần tải bộ cài Odoo hay thư mục `odoo-core` về máy không?

**KHÔNG CẦN!**
* Bạn **không cần** tải bộ cài Odoo cho Windows/Mac và cũng **không cần** tải thư mục mã nguồn `odoo-core`.
* Khi bạn chạy lệnh `docker compose up -d`, **Docker sẽ tự động tải bản Odoo 18.0 chính thức** (`image: odoo:18.0`) về máy và tự động gắn thư mục `custom_addons/` của nhóm vào bên trong hệ thống.

---

## 🚀 Hướng dẫn cài đặt chi tiết cho người mới (Từ A - Z)

### Bước 1: Cài đặt các phần mềm cần thiết
Nếu máy bạn chưa có **Git** và **Docker Desktop**, hãy tải và cài đặt:
1. **Git:** [Tải tại git-scm.com](https://git-scm.com/downloads) (Cài đặt bấm *Next* mặc định).
2. **Docker Desktop:** [Tải tại docker.com](https://www.docker.com/products/docker-desktop/)
   * Sau khi cài xong Docker Desktop, hãy khởi động lại máy tính (nếu được yêu cầu).
   * Mở ứng dụng **Docker Desktop** lên và đợi góc dưới bên trái hiện trạng thái màu xanh (**Engine running**).

---

### Bước 2: Tải dự án từ GitHub về máy
Mở **PowerShell** hoặc **Command Prompt (CMD)** (hoặc Terminal trong VS Code), di chuyển đến thư mục bạn muốn lưu dự án và chạy lệnh:

```powershell
git clone https://github.com/24521021-collab/IS336.git
cd IS336
```

---

### Bước 3: Khởi động Odoo
Tại thư mục `IS336`, chạy lệnh:

```powershell
docker compose up -d
```

* **Lưu ý cho lần chạy đầu tiên:** Docker sẽ tự động tải image `odoo:18.0` (khoảng vài trăm MB) về máy. Quá trình này mất khoảng **2 – 5 phút** tùy tốc độ mạng.
* Khi màn hình hiện `Container is336-web-1 Started`, nghĩa là Odoo đã chạy thành công!

---

### Bước 4: Truy cập và Đăng nhập vào Odoo
1. Đợi khoảng **15 – 30 giây** để Odoo kết nối tới database trên Cloud.
2. Mở trình duyệt web (Chrome, Edge...) và truy cập địa chỉ:
   👉 **http://localhost:8069**
3. Đăng nhập bằng tài khoản quản trị mặc định của nhóm:
   * **Email / Tên đăng nhập:** `admin`
   * **Mật khẩu:** `admin`

---

## 🔄 Các lệnh thường dùng hàng ngày

| Mục đích | Lệnh chạy trong Terminal (tại thư mục `IS336`) |
| :--- | :--- |
| **1. Cập nhật code mới nhất từ nhóm** | `git pull origin main` rồi chạy `docker compose restart web` |
| **2. Bật Odoo lên để làm việc** | `docker compose up -d` |
| **3. Tắt Odoo khi nghỉ** | `docker compose stop` |
| **4. Xem nhật ký (log) để kiểm tra lỗi** | `docker compose logs -f` *(Bấm `Ctrl + C` để thoát xem log)* |
| **5. Khởi động lại Odoo** | `docker compose restart web` |

---

## 📦 Tính năng tùy chỉnh đã tích hợp sẵn (`custom_addons/is336_product_setup`)

Hệ thống đã được cài đặt sẵn module tùy chỉnh **`is336_product_setup`** với các chức năng tự động:

1. **5 Nhóm sản phẩm chính (`Product Category`):**
   * `Đồ uống`
   * `Đồ ăn nhanh`
   * `Ăn vặt`
   * `Hàng thiết yếu`
   * `Đồ dùng cá nhân/học tập`
2. **Tự động tạo & quy đổi Đơn vị tính (`Unit of Measure`):**
   * Tự động tạo mới đơn vị tính từ file CSV/Excel của crawler nếu trong Odoo chưa có (`Hộp`, `Lon`, `Chai`, `Gói`, `Bịch`, `Ly`, `Cây`, `Quyển`...).
   * Tự động phân tích quy cách đóng gói từ **Tên sản phẩm**. Ví dụ:
     * Tên sản phẩm: `Lốc 4 hộp sữa lúa mạch ít đường Milo A2 180ml`
     * Hệ thống tự động tạo đơn vị gốc `Hộp` (tỷ lệ `1.0`), tạo đơn vị đóng gói `Lốc 4 hộp` với tỷ lệ **`1 Lốc 4 hộp = 4 Hộp`**, và tự động gán cho sản phẩm.
   * **Cập nhật hàng loạt cho sản phẩm cũ:** Vào **Products ➔ Products** (chế độ danh sách List View) ➔ Tích chọn sản phẩm ➔ Bấm **Actions (Hành động) ➔ Tự động nhận diện Đơn vị tính từ Tên SP**.

---

## ⚠️ Quy tắc quan trọng khi làm việc nhóm trên Database chung

Vì cả nhóm kết nối chung vào 1 cơ sở dữ liệu `neondb`:
1. **Không tự ý bấm Install / Upgrade / Uninstall các ứng dụng lớn** trong mục *Apps* cùng lúc mà không báo trước cho nhóm.
2. Khi một thành viên thêm/sửa code trong thư mục `custom_addons/`, hãy báo cho các thành viên khác chạy `git pull origin main` và `docker compose restart web` để đồng bộ mã nguồn.
3. Để tránh xóa nhầm dữ liệu có liên kết của thành viên khác, khi muốn ẩn sản phẩm mẫu/cũ, hãy ưu tiên dùng chức năng **Actions ➔ Archive (Lưu trữ)** thay vì *Delete (Xóa)*.
