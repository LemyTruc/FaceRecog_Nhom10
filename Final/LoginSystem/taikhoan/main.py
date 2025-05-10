import sys
import csv
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox, QTableWidgetItem, QHeaderView
from PyQt6 import QtWidgets, uic
import csv_handler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime



class giaoDienDangNhap(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("giao_dien_dang_nhap.ui", self)
        self.pushButtonDangNhap.clicked.connect(self.dangNhap)

        # Load and apply CSS
        with open('style.css', 'r') as f:
            style = f.read()
            self.setStyleSheet(style)

    
    def chuyenGiaoDienChinh(self):
        self.window = giaoDienChinh()
        self.window.show()
        self.hide()

    def dangNhap(self):
        tai_khoan = self.lineEditTaiKhoan.text()
        mat_khau = self.lineEditMatKhau.text()

        data = csv_handler.read_data_from_csv()
        for row in data:
            if row[0] == tai_khoan:
                if row[1] == mat_khau:
                    QMessageBox.information(self, "Notification", "Login successful")
                    self.chuyenGiaoDienChinh()
                    return
                else:
                    QMessageBox.warning(self, "Notification", "You entered the wrong password")
                    return

        QMessageBox.warning(self, "Notification", "The account just entered does not exist")


class giaoDienChinh(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("giao_dien_Admin.ui", self)
        self.pushButtonLogout.clicked.connect(self.dangXuat)
        self.pushButtonGuiYeuCau.clicked.connect(self.guiEmailHoTro)
    def dangXuat(self):
        self.window = giaoDienDangNhap()
        self.window.show()
        self.hide()
    def guiEmailHoTro(self):
        tieu_de = self.lineEditTieuDe.text()
        noi_dung = self.textEditNoiDung.toPlainText()
        thoi_gian_gui = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not tieu_de or not noi_dung:
            QMessageBox.warning(self, "Notification", "Please enter full title and content.")
            return

        try:
            # Thông tin email
            email_gui = "mytruckrbm@gmail.com"
            mat_khau = "lkmv fodc zsgj dklf"
            email_nhan = "trucle.31221026452@st.ueh.edu.vn"

            # Cấu hình nội dung email
            msg = MIMEMultipart()
            msg["From"] = email_gui
            msg["To"] = email_nhan
            msg["Subject"] = f"Support request: {tieu_de}"
            body = f"Content of support request from Admin:\n\n{noi_dung}"
            msg.attach(MIMEText(body, "plain"))

            # Kết nối và gửi email
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(email_gui, mat_khau)
            server.sendmail(email_gui, email_nhan, msg.as_string())
            server.quit()

            # Lưu vào danh sách hỗ trợ
            with open("danh_sach_ho_tro.csv", mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([tieu_de, noi_dung,thoi_gian_gui])

            QMessageBox.information(self, "Notification", "Support request has been submitted successfully.")

            # Cập nhật danh sách hỗ trợ
            self.hienThiDanhSachHoTro()

        except Exception as e:
            QMessageBox.warning(self, "Notification", f"Email sending failed: {str(e)}")

    def hienThiDanhSachHoTro(self):
        try:
            with open("danh_sach_ho_tro.csv", mode="r", encoding="utf-8") as file:
                reader = csv.reader(file)
                danh_sach = list(reader)

            self.tableWidgetHoTro.setRowCount(len(danh_sach))
            self.tableWidgetHoTro.setColumnCount(3)
            self.tableWidgetHoTro.setHorizontalHeaderLabels(["Title", "Content", "Time"])

            for row_index, row_data in enumerate(danh_sach):
                for col_index, cell_data in enumerate(row_data):
                    self.tableWidgetHoTro.setItem(row_index, col_index, QTableWidgetItem(cell_data))

            self.tableWidgetHoTro.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

        except FileNotFoundError:
            QMessageBox.warning(self, "Notification", "No support list found.")

khoiChayHeThong = QApplication(sys.argv)
phanMem = giaoDienDangNhap()
phanMem.show()
chayPhanMem = khoiChayHeThong.exec()
sys.exit(chayPhanMem)