import sys
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox, QTableWidgetItem, QHeaderView
from PyQt6 import QtWidgets, uic
import csv_handler

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
                    QMessageBox.information(self, "Thông báo", "Đăng nhập thành công")
                    self.chuyenGiaoDienChinh()
                    return
                else:
                    QMessageBox.warning(self, "Thông báo", "Bạn nhập sai mật khẩu")
                    return

        QMessageBox.warning(self, "Thông báo", "Tài khoản vừa nhập không tồn tại")
    
class giaoDienChinh(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("giao_dien_Admin.ui", self)
        self.pushButtonLogout.clicked.connect(self.dangXuat)

    def dangXuat(self):
        self.window = giaoDienDangNhap()
        self.window.show()
        self.hide()

khoiChayHeThong = QApplication(sys.argv)
phanMem = giaoDienDangNhap()
phanMem.show()
chayPhanMem = khoiChayHeThong.exec()
sys.exit(chayPhanMem)