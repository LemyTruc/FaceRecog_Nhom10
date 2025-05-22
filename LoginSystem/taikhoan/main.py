import sys
import os
import subprocess
import csv
import json
from PyQt6.QtWidgets import (QMainWindow, QApplication, QMessageBox, QTableWidgetItem, 
                          QHeaderView, QFileDialog, QPushButton, QDialog, QVBoxLayout, 
                          QHBoxLayout, QLabel, QLineEdit)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt  
from shutil import copy2
from PyQt6 import QtWidgets, uic
import csv_handler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Get the directory containing the script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
STUDENTS_DIR = os.path.join(PROJECT_ROOT, "students")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Create necessary directories
os.makedirs(STUDENTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

class giaoDienDangNhap(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load UI file using absolute path
        ui_file = os.path.join(CURRENT_DIR, "giao_dien_dang_nhap.ui")
        uic.loadUi(ui_file, self)
        self.pushButtonDangNhap.clicked.connect(self.dangNhap)

        # Load and apply CSS
        css_file = os.path.join(CURRENT_DIR, "style.css")
        with open(css_file, 'r') as f:
            style = f.read()
            self.setStyleSheet(style)
        
        # Connect the UI button instead
        self.commandLinkButtonSignUp.clicked.connect(self.openAttendanceSystem)
        
        # Add flag to track if attendance system is running
        self.attendance_running = False

    def chuyenGiaoDienChinh(self):
        self.window = giaoDienChinh()
        self.window.show()
        self.hide()

    def dangNhap(self):
        """Improved login handling"""
        tai_khoan = self.lineEditTaiKhoan.text().strip()
        mat_khau = self.lineEditMatKhau.text().strip()
        
        if not tai_khoan or not mat_khau:
            QMessageBox.warning(self, "Notification", "Please enter both username and password")
            return

        try:
            data = csv_handler.read_data_from_csv()
            if not data:
                QMessageBox.warning(self, "Error", "User database is empty")
                return
                
            # Convert to dictionary for faster lookup
            users = {row[0]: row[1] for row in data if len(row) >= 2}
            
            if tai_khoan not in users:
                QMessageBox.warning(self, "Notification", "Account does not exist")
                return
                
            if users[tai_khoan] != mat_khau:
                QMessageBox.warning(self, "Notification", "Incorrect password")
                return
                
            QMessageBox.information(self, "Notification", "Login successful")
            self.chuyenGiaoDienChinh()
            
        except Exception as e:
            print(f"Error during login: {str(e)}")
            QMessageBox.critical(self, "Error", "An error occurred during login")

    def openAttendanceSystem(self):
        """Improved attendance system launch"""
        if self.attendance_running:
            QMessageBox.warning(self, "Warning", "Attendance system is already running")
            return
            
        try:
            attendance_path = os.path.join(CURRENT_DIR, "..", "..", "AttendenceSystem", "facereg", "main.py")
            if not os.path.exists(attendance_path):
                raise FileNotFoundError(f"Attendance system not found at: {attendance_path}")
                
            # Use Popen with shell=False for security
            subprocess.Popen([sys.executable, attendance_path], shell=False)
            
            self.attendance_running = True
            self.close()
                
        except Exception as e:
            print(f"Error launching attendance system: {str(e)}")
            QMessageBox.critical(self, "Error", "Failed to launch attendance system")


class giaoDienChinh(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load UI file using absolute path
        ui_file = os.path.join(CURRENT_DIR, "giao_dien_Admin.ui")
        uic.loadUi(ui_file, self)
        
        # Connect buttons
        self.pushButtonLogout.clicked.connect(self.dangXuat)
        self.pushButtonGuiYeuCau.clicked.connect(self.guiEmailHoTro)
        
        # Connect student management buttons
        self.pushButtonThem.clicked.connect(self.themSinhVien)
        self.pushButtonSua.clicked.connect(self.suaThongTin)
        
        # Connect delete button
        if hasattr(self, 'pushButtonXoa'):
            self.pushButtonXoa.clicked.connect(self.deleteStudent)
        
        # FIXED: Connect search button properly
        if hasattr(self, 'pushButtonTimKiem'):
            self.pushButtonTimKiem.clicked.connect(self.searchStudent)
        
        # Initialize tables
        self.setupTables()
        
        # Load initial data
        self.hienThiDanhSachHoTro()
        self.loadAttendanceHistory()
        self.loadStudentData()

    def setupTables(self):
        # Setup Support table
        self.tableWidgetHoTro.setColumnCount(3)
        self.tableWidgetHoTro.setHorizontalHeaderLabels(["Title", "Content", "Time"])
        self.tableWidgetHoTro.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Setup History table as read-only
        self.historyTable.setColumnCount(4)
        self.historyTable.setHorizontalHeaderLabels(["Name", "Student ID", "Date", "Time"])
        self.historyTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.historyTable.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.historyTable.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.historyTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Optional: Add style to show it's read-only
        self.historyTable.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #2d4057;
                color: white;
            }
        """)
        
        # Setup Student table
        self.tableWidgetSinhVien.setColumnCount(7)
        self.tableWidgetSinhVien.setHorizontalHeaderLabels([
            "Mã SV", "Họ và tên", "Lớp", "Khoa", 
            "Email", "Phone number", "Image Path"
        ])
        self.tableWidgetSinhVien.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Connect selection changed event
        self.tableWidgetSinhVien.itemSelectionChanged.connect(self.onStudentSelected)

    def loadAttendanceHistory(self):
        try:
            history_file = os.path.join(CURRENT_DIR, "..", "..", "attendance_history.json")
            print(f"Looking for attendance history at: {history_file}")
            
            if not os.path.exists(history_file):
                print(f"File not found: {history_file}")
                os.makedirs(os.path.dirname(history_file), exist_ok=True)
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                return

            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
                
            if not history:
                print("History file is empty")
                return
                
            # Sort history by date and time (newest first)
            sorted_history = sorted(
                history, 
                key=lambda x: (x["date"], x["time"]),
                reverse=True
            )
            
            # Update table
            self.historyTable.setRowCount(len(sorted_history))
            for row, record in enumerate(sorted_history):
                self.historyTable.setItem(row, 0, QTableWidgetItem(record["name"]))
                self.historyTable.setItem(row, 1, QTableWidgetItem(record["student_id"]))
                self.historyTable.setItem(row, 2, QTableWidgetItem(record["date"]))
                self.historyTable.setItem(row, 3, QTableWidgetItem(record["time"]))
            
            print(f"Loaded {len(sorted_history)} attendance records")
        
        except FileNotFoundError:
            print("Attendance history file not found")
            QMessageBox.warning(self, "Notification", "No attendance history found.")
        except json.JSONDecodeError as e:
            print(f"Error parsing attendance history: {e}")
            QMessageBox.warning(self, "Notification", "Invalid attendance history file format")
        except Exception as e:
            print(f"Error loading attendance history: {str(e)}")
            QMessageBox.warning(self, "Notification", f"Error loading attendance history: {str(e)}")

    def guiEmailHoTro(self):
        tieu_de = self.lineEditTieuDe.text()
        noi_dung = self.textEditNoiDung.toPlainText()
        thoi_gian_gui = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not tieu_de or not noi_dung:
            QMessageBox.warning(self, "Notification", "Please enter full title and content.")
            return

        try:
            # Email configuration
            email_gui = "mytruckrbm@gmail.com"
            mat_khau = "lkmv fodc zsgj dklf"
            email_nhan = "trucle.31221026452@st.ueh.edu.vn"

            # Setup email content
            msg = MIMEMultipart()
            msg["From"] = email_gui
            msg["To"] = email_nhan
            msg["Subject"] = f"Support request: {tieu_de}"
            body = f"Content of support request from Admin:\n\n{noi_dung}"
            msg.attach(MIMEText(body, "plain"))

            # Connect and send email
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(email_gui, mat_khau)
            server.sendmail(email_gui, email_nhan, msg.as_string())
            server.quit()

            support_file = os.path.join(CURRENT_DIR, "danh_sach_ho_tro.csv")
            
            # Save to support list
            file_exists = os.path.exists(support_file)
            with open(support_file, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["Title", "Content", "Time"])
                writer.writerow([tieu_de, noi_dung, thoi_gian_gui])

            QMessageBox.information(self, "Notification", "Support request has been submitted successfully.")

            # Update support list
            self.hienThiDanhSachHoTro()

        except Exception as e:
            print(f"Email error: {str(e)}")
            QMessageBox.warning(self, "Notification", f"Email sending failed: {str(e)}")

    def hienThiDanhSachHoTro(self):
        try:
            support_file = os.path.join(CURRENT_DIR, "danh_sach_ho_tro.csv")
            if not os.path.exists(support_file):
                with open(support_file, mode="w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Title", "Content", "Time"])
                QMessageBox.information(self, "Notification", "Created new support list file.")
                return

            with open(support_file, mode="r", encoding="utf-8") as file:
                reader = csv.reader(file)
                danh_sach = list(reader)

            self.tableWidgetHoTro.setRowCount(len(danh_sach))
            for row_index, row_data in enumerate(danh_sach):
                for col_index, cell_data in enumerate(row_data):
                    if col_index < 3:
                        self.tableWidgetHoTro.setItem(row_index, col_index, QTableWidgetItem(cell_data))

        except Exception as e:
            print(f"Error displaying support list: {str(e)}")
            QMessageBox.warning(self, "Notification", f"Error loading support list: {str(e)}")

    def dangXuat(self):
        self.window = giaoDienDangNhap()
        self.window.show()
        self.hide()

    def themSinhVien(self):
        """Add new student with photo"""
        ma_sv = self.lineEditMaSV.text().strip()
        ho_ten = self.lineEditHoTen.text().strip()
        
        if not ma_sv or not ho_ten:
            QMessageBox.warning(self, "Error", "Please enter Student ID and Name")
            return
            
        # Select student photo
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Student Photo",
            "",
            "Image files (*.jpg *.jpeg *.png)"
        )
        
        if not file_name:
            reply = QMessageBox.question(
                self, "No Photo", 
                "No photo selected. Continue without photo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            new_photo_path = ""
        else:
            try:
                os.makedirs(STUDENTS_DIR, exist_ok=True)
                photo_ext = os.path.splitext(file_name)[1]
                new_photo_path = os.path.join(STUDENTS_DIR, f"{ma_sv}{photo_ext}")
                copy2(file_name, new_photo_path)
            except Exception as e:
                print(f"Error copying photo: {str(e)}")
                QMessageBox.warning(self, "Error", f"Failed to copy photo: {str(e)}")
                new_photo_path = ""
            
        try:    
            csv_path = os.path.join(DATA_DIR, "student_data.csv")
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            fieldnames = ['student_id', 'name', 'class', 'department', 'email', 'phone', 'image_path']
            students = []
            
            if os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    students = list(reader)
            
            # Check for duplicate ID
            if any(s.get('student_id') == ma_sv for s in students):
                QMessageBox.warning(self, "Error", "Student ID already exists")
                return
            
            # Add new student
            students.append({
                'student_id': ma_sv,
                'name': ho_ten,
                'class': self.lineEditLop.text(),
                'department': self.lineEditKhoa.text(),
                'email': self.lineEditEmail.text(),
                'phone': self.lineEditSDT.text(),
                'image_path': new_photo_path
            })
            
            # Write back to CSV
            with open(csv_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(students)
            
            QMessageBox.information(self, "Success", "Student added successfully")
            self.loadStudentData()
            self.clearForm()
            
        except Exception as e:
            print(f"Error adding student: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add student: {str(e)}")

    def suaThongTin(self):
        """Edit student information including photo"""
        ma_sv = self.lineEditMaSV.text().strip()
        if not ma_sv:
            selected_rows = self.tableWidgetSinhVien.selectedItems()
            if not selected_rows:
                QMessageBox.warning(self, "Error", "Please select a student or enter Student ID")
                return
            
            ma_sv = self.tableWidgetSinhVien.item(selected_rows[0].row(), 0).text()
            
        try:
            csv_path = os.path.join(DATA_DIR, "student_data.csv")
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Error", "Student database not found")
                return
            
            students = []
            student_found = False
            
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                students = list(reader)
                if not students:
                    QMessageBox.warning(self, "Error", "Student database is empty")
                    return
            
            for student in students:
                if student.get('student_id') == ma_sv:
                    student_found = True
                    
                    if QMessageBox.question(self, "Update Photo",
                        "Do you want to update student's photo?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                        
                        file_name, _ = QFileDialog.getOpenFileName(
                            self, "Select New Photo", "", "Image files (*.jpg *.jpeg *.png)")
                        
                        if file_name:
                            os.makedirs(STUDENTS_DIR, exist_ok=True)
                            photo_ext = os.path.splitext(file_name)[1]
                            new_photo_path = os.path.join(STUDENTS_DIR, f"{ma_sv}{photo_ext}")
                            copy2(file_name, new_photo_path)
                            student['image_path'] = new_photo_path
                    
                    # Update other information
                    student.update({
                        'name': self.lineEditHoTen.text(),
                        'class': self.lineEditLop.text(),
                        'department': self.lineEditKhoa.text(),
                        'email': self.lineEditEmail.text(),
                        'phone': self.lineEditSDT.text()
                    })
                    break
            
            if not student_found:
                QMessageBox.warning(self, "Error", f"Student with ID {ma_sv} not found")
                return
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as file:
                fieldnames = ['student_id', 'name', 'class', 'department', 'email', 'phone', 'image_path']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(students)
            
            QMessageBox.information(self, "Success", "Student information updated successfully")
            self.loadStudentData()
        
        except Exception as e:
            print(f"Error updating student: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to update student information: {str(e)}")

    def clearForm(self):
        """Clear all form fields"""
        self.lineEditMaSV.clear()
        self.lineEditHoTen.clear()
        self.lineEditLop.clear()
        self.lineEditKhoa.clear()
        self.lineEditEmail.clear()
        self.lineEditSDT.clear()

    def loadStudentData(self):
        """Improved student data loading"""
        try:
            csv_path = os.path.join(DATA_DIR, "student_data.csv")
            fieldnames = ['student_id', 'name', 'class', 'department', 'email', 'phone', 'image_path']
            
            if not os.path.exists(csv_path):
                os.makedirs(os.path.dirname(csv_path), exist_ok=True)
                with open(csv_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                return
                
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                students = list(reader)
                
            students.sort(key=lambda x: x.get('student_id', ''))
                
            self.tableWidgetSinhVien.setRowCount(len(students))
            for row, student in enumerate(students):
                for col, field in enumerate(fieldnames):
                    self.tableWidgetSinhVien.setItem(row, col, 
                        QTableWidgetItem(student.get(field, '')))
                        
            print(f"Loaded {len(students)} students")
                
        except Exception as e:
            print(f"Error loading student data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load student data: {str(e)}")

    def onStudentSelected(self):
        """Handle student selection from table"""
        selected_items = self.tableWidgetSinhVien.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        
        try:
            self.lineEditMaSV.setText(self.tableWidgetSinhVien.item(row, 0).text())
            self.lineEditHoTen.setText(self.tableWidgetSinhVien.item(row, 1).text())
            self.lineEditLop.setText(self.tableWidgetSinhVien.item(row, 2).text())
            self.lineEditKhoa.setText(self.tableWidgetSinhVien.item(row, 3).text())
            self.lineEditEmail.setText(self.tableWidgetSinhVien.item(row, 4).text())
            self.lineEditSDT.setText(self.tableWidgetSinhVien.item(row, 5).text())
        except Exception as e:
            print(f"Error filling form: {str(e)}")

    def deleteStudent(self):
        """Delete selected student"""
        selected_items = self.tableWidgetSinhVien.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a student to delete")
            return
            
        row = selected_items[0].row()
        student_id = self.tableWidgetSinhVien.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete student {student_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                csv_path = os.path.join(DATA_DIR, "student_data.csv")
                if not os.path.exists(csv_path):
                    QMessageBox.warning(self, "Error", "Student database not found")
                    return
                    
                with open(csv_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    students = list(reader)
                    if not students:
                        QMessageBox.warning(self, "Error", "Student database is empty")
                        return
                
                image_path = ""
                updated_students = []
                student_deleted = False
                
                for student in students:
                    if student.get('student_id') == student_id:
                        image_path = student.get('image_path', '')
                        student_deleted = True
                    else:
                        updated_students.append(student)
                
                if not student_deleted:
                    QMessageBox.warning(self, "Error", "Student not found in database")
                    return
                
                with open(csv_path, 'w', newline='', encoding='utf-8') as file:
                    fieldnames = ['student_id', 'name', 'class', 'department', 'email', 'phone', 'image_path']
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(updated_students)
                
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                        print(f"Deleted image: {image_path}")
                    except Exception as e:
                        print(f"Failed to delete image: {str(e)}")
                
                self.loadStudentData()
                self.clearForm()
                QMessageBox.information(self, "Success", "Student deleted successfully")
                
            except Exception as e:
                print(f"Error deleting student: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to delete student: {str(e)}")

    def searchStudent(self):
        """FIXED: Search students and display only matching results"""
        # Get values from input fields
        student_id = self.lineEditMaSV.text().strip().lower()
        name = self.lineEditHoTen.text().strip().lower()
        class_name = self.lineEditLop.text().strip().lower()
        department = self.lineEditKhoa.text().strip().lower()
        email = self.lineEditEmail.text().strip().lower()
        phone = self.lineEditSDT.text().strip().lower()
        
        # If all fields are empty, show all records
        if not any([student_id, name, class_name, department, email, phone]):
            self.loadStudentData()  # Reload all data
            return

        try:
            csv_path = os.path.join(DATA_DIR, "student_data.csv")
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Error", "Student database not found")
                return

            matching_students = []
            
            # Read and filter data
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for student in reader:
                    # Check if student matches search criteria (case insensitive)
                    if (
                        (not student_id or student_id in student.get('student_id', '').lower()) and
                        (not name or name in student.get('name', '').lower()) and
                        (not class_name or class_name in student.get('class', '').lower()) and
                        (not department or department in student.get('department', '').lower()) and
                        (not email or email in student.get('email', '').lower()) and
                        (not phone or phone in student.get('phone', '').lower())
                    ):
                        matching_students.append(student)

            # Update table with matching results
            fieldnames = ['student_id', 'name', 'class', 'department', 'email', 'phone', 'image_path']
            self.tableWidgetSinhVien.setRowCount(len(matching_students))
            
            for row, student in enumerate(matching_students):
                for col, field in enumerate(fieldnames):
                    self.tableWidgetSinhVien.setItem(row, col, 
                        QTableWidgetItem(student.get(field, '')))

            # Show message with results count
            if not matching_students:
                QMessageBox.information(self, "Search Result", "No matching students found")
            else:
                QMessageBox.information(self, "Search Result", 
                    f"Found {len(matching_students)} matching student(s)")
                
        except Exception as e:
            print(f"Error searching students: {str(e)}")
            QMessageBox.critical(self, "Error", f"Search failed: {str(e)}")


# Main execution
khoiChayHeThong = QApplication(sys.argv)
phanMem = giaoDienDangNhap()
phanMem.show()
chayPhanMem = khoiChayHeThong.exec()
sys.exit(chayPhanMem)