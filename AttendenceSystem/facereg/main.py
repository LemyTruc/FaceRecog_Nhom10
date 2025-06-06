import sys
import csv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, 
                           QVBoxLayout, QHBoxLayout, QWidget, QFrame, QTableWidget, 
                           QTableWidgetItem, QTabWidget, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage
from datetime import datetime
import json
import os
import subprocess

from face_reg import FaceRecognitionWebcam
from eye_track import EyeTrackingWebcam

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
STUDENTS_DIR = os.path.join(PROJECT_ROOT, "students")

class AttendanceSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.setWindowTitle("Smart Face Attendance System")
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet("background-color: #0f192d;")
        
        # Load student data from CSV
        self.student_data = self.load_student_data()
        
        # Load attendance history
        self.load_attendance_history()
        
        # Set up UI
        self.setup_ui()
        
        # Current mode
        self.current_mode = "idle"  # idle, face_recognition, second_webcam, completed
        
        # Timer for updating UI
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(1000)  # Update every second
        
        # Track students who have already checked in during this session
        self.session_check_ins = set()
        
    def load_student_data(self):
        """Tải dữ liệu học sinh từ tệp CSV trong thư mục data"""
        students = []
        csv_path = os.path.join(DATA_DIR, "student_data.csv")
        
        print(f"Đang tải dữ liệu học sinh từ: {csv_path}")
        
        if not os.path.exists(csv_path):
            print(f"Lỗi: Không tìm thấy tệp {csv_path}")
            QMessageBox.critical(self, "Lỗi", f"Không tìm thấy tệp {csv_path}")
            return students
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                expected_fields = ['student_id', 'name', 'image_path']
                if not all(field in reader.fieldnames for field in expected_fields):
                    print(f"Lỗi: Tệp CSV thiếu các cột cần thiết: {expected_fields}")
                    QMessageBox.critical(self, "Lỗi", "Tệp CSV có định dạng không đúng")
                    return students
                
                for row in reader:
                    if row['student_id'] and row['name'] and row['image_path']:
                        image_path = row['image_path']
                        # Kiểm tra xem ảnh có tồn tại không
                        if os.path.exists(image_path):
                            students.append({
                                "name": row['name'],
                                "id": row['student_id'],
                                "image_path": image_path
                            })
                        else:
                            print(f"Cảnh báo: Không tìm thấy ảnh tại {image_path}")
                print(f"Đã tải {len(students)} bản ghi học sinh từ {csv_path}")
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu học sinh: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi tải dữ liệu học sinh: {str(e)}")
            students = []
            
        return students

    def setup_ui(self):
        # Create history_table at the start of setup_ui
        self.history_table = QTableWidget()

        # Main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Left panel for camera
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #19293d; border-radius: 15px;")
        left_layout = QVBoxLayout(left_panel)
        
        # Camera view
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setStyleSheet("border: 2px solid #2d3e50; border-radius: 10px;")
        left_layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Camera status label
        self.status_label = QLabel("Ready to start attendance check")
        self.status_label.setStyleSheet("color: #99a3b1; font-size: 16px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.status_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Start button
        self.start_btn = QPushButton("Start Attendance")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.start_btn.setFixedHeight(50)
        self.start_btn.clicked.connect(self.start_attendance)
        button_layout.addWidget(self.start_btn)
        
        # Continue button
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9933;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff8800;
            }
            QPushButton:pressed {
                background-color: #e07000;
            }
        """)
        self.continue_btn.setFixedHeight(50)
        self.continue_btn.clicked.connect(self.continue_to_next)
        self.continue_btn.setVisible(False)  # Initially hidden
        button_layout.addWidget(self.continue_btn)
        
        # End button
        self.end_btn = QPushButton("End Attendance")
        self.end_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
        """)
        self.end_btn.setFixedHeight(50)
        self.end_btn.clicked.connect(self.end_attendance)
        self.end_btn.setVisible(False)  # Initially hidden
        button_layout.addWidget(self.end_btn)
        
        # Back to Login button
        self.back_btn = QPushButton("Back to Login")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.back_btn.setFixedHeight(50)
        self.back_btn.clicked.connect(self.back_to_login)
        button_layout.addWidget(self.back_btn)
        
        left_layout.addLayout(button_layout)
        
        # Right panel with tabs
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #19293d; border-radius: 15px;")
        right_layout = QVBoxLayout(right_panel)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2d3e50;
                border-radius: 5px;
                background-color: #1e3349;
            }
            QTabBar::tab {
                background-color: #19293d;
                color: #99a3b1;
                padding: 10px 20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #2d4057;
                color: white;
            }
        """)
        
        # Recognition tab only
        recognition_tab = QWidget()
        recognition_layout = QVBoxLayout(recognition_tab)
        
        # Current datetime
        self.datetime_label = QLabel()
        self.datetime_label.setStyleSheet("color: #99a3b1; font-size: 14px;")
        self.datetime_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        recognition_layout.addWidget(self.datetime_label)
        
        # Recognition info panel
        info_panel = QFrame()
        info_panel.setStyleSheet("background-color: #1e3349; border-radius: 10px; padding: 20px;")
        info_layout = QVBoxLayout(info_panel)
        
        # Header
        header_label = QLabel("STUDENT INFORMATION")
        header_label.setStyleSheet("color: #99ccff; font-size: 18px; font-weight: bold;")
        info_layout.addWidget(header_label)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #2d4057; max-height: 1px;")
        info_layout.addWidget(separator)
        info_layout.addSpacing(20)
        
        # Student photo
        photo_layout = QHBoxLayout()
        photo_label = QLabel("Photo:")
        photo_label.setStyleSheet("color: #99a3b1; font-size: 16px;")
        self.student_photo = QLabel()
        self.student_photo.setFixedSize(120, 160)
        self.student_photo.setStyleSheet("background-color: #2d3e50; border-radius: 5px;")
        self.student_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_layout.addWidget(photo_label)
        photo_layout.addWidget(self.student_photo)
        info_layout.addLayout(photo_layout)
        info_layout.addSpacing(20)
        
        # Student info
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_label.setStyleSheet("color: #99a3b1; font-size: 16px;")
        self.name_value = QLabel("Not recognized")
        self.name_value.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_value)
        info_layout.addLayout(name_layout)
        info_layout.addSpacing(10)
        
        id_layout = QHBoxLayout()
        id_label = QLabel("ID:")
        id_label.setStyleSheet("color: #99a3b1; font-size: 16px;")
        self.id_value = QLabel("Not recognized")
        self.id_value.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        id_layout.addWidget(id_label)
        id_layout.addWidget(self.id_value)
        info_layout.addLayout(id_layout)
        info_layout.addSpacing(10)
        
        time_layout = QHBoxLayout()
        time_label = QLabel("Check-in time:")
        time_label.setStyleSheet("color: #99a3b1; font-size: 16px;")
        self.time_value = QLabel("--:--:--")
        self.time_value.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.time_value)
        info_layout.addLayout(time_layout)
        info_layout.addSpacing(20)
        
        # Status message
        self.status_message = QLabel("Ready to start attendance")
        self.status_message.setStyleSheet("color: #99a3b1; font-size: 16px; font-weight: bold;")
        self.status_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.status_message)
        
        recognition_layout.addWidget(info_panel)
        
        # Add single tab to widget
        self.tab_widget.addTab(recognition_tab, "Recognition")
        
        right_layout.addWidget(self.tab_widget)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 3)
        main_layout.addWidget(right_panel, 2)
        
    def start_attendance(self):
        """Start the face recognition webcam"""
        self.current_mode = "face_recognition"
        
        # Update UI
        self.status_label.setText("Face Recognition Mode - Position your face in the camera")
        self.status_label.setStyleSheet("color: #99a3b1; font-size: 16px;")
        self.status_message.setText("Waiting for face recognition...")
        self.status_message.setStyleSheet("color: #99a3b1; font-size: 16px;")
        
        # Hide start button, show continue button
        self.start_btn.setVisible(False)
        self.continue_btn.setVisible(True)
        self.continue_btn.setEnabled(False)  # Enable after face is recognized
        self.end_btn.setVisible(False)
        
        # Initialize the face recognition webcam module
        self.face_recognition_webcam = FaceRecognitionWebcam(self.student_data)
        self.face_recognition_webcam.frame_ready.connect(self.update_camera_feed)
        self.face_recognition_webcam.face_detected.connect(self.handle_face_detected)
        self.face_recognition_webcam.start()
    
    def continue_to_next(self):
        """Continue to the next step based on current mode"""
        if self.current_mode == "face_recognition":
            # Stop face recognition webcam
            if hasattr(self, 'face_recognition_webcam'):
                self.face_recognition_webcam.stop()
            
            # Change to eye tracking mode
            self.current_mode = "eye_tracking"
            
            # Update UI
            self.status_label.setText("Eye Tracking Test Mode")
            self.status_label.setStyleSheet("color: #99a3b1; font-size: 16px;")
            self.status_message.setText("Follow the eye movement instructions...")
            self.status_message.setStyleSheet("color: #99a3b1; font-size: 16px;")
            
            # Hide continue button during test
            self.continue_btn.setVisible(False)
            self.end_btn.setVisible(False)
            
            # Initialize eye tracking
            self.eye_tracking = EyeTrackingWebcam()
            self.eye_tracking.frame_ready.connect(self.update_camera_feed)
            self.eye_tracking.test_completed.connect(self.handle_eye_test_completed)
            self.eye_tracking.start()

    def handle_eye_test_completed(self, passed):
        """Handle completion of eye tracking test"""
        if passed:
            self.status_message.setText("Eye tracking test passed!")
            self.status_message.setStyleSheet("color: #00c853; font-size: 16px;")
            # Show end button
            self.end_btn.setVisible(True)
        else:
            self.status_message.setText("Eye tracking test failed - Please try again")
            self.status_message.setStyleSheet("color: #f44336; font-size: 16px;")
            # Return to face recognition
            self.start_attendance()
    
    def end_attendance(self):
        """End the attendance process"""
        # Stop second webcam if running
        if hasattr(self, 'second_webcam'):
            self.second_webcam.stop()
        
        # Reset to idle mode
        self.current_mode = "idle"
        
        # Update UI
        self.status_label.setText("Ready to start attendance check")
        self.status_label.setStyleSheet("color: #99a3b1; font-size: 16px;")
        self.status_message.setText("Ready to start attendance")
        self.status_message.setStyleSheet("color: #99a3b1; font-size: 16px;")
        
        # Reset student info
        self.name_value.setText("Not recognized")
        self.id_value.setText("Not recognized")
        self.time_value.setText("--:--:--")
        self.student_photo.clear()
        self.student_photo.setText("No Photo")
        self.student_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Show start button, hide other buttons
        self.start_btn.setVisible(True)
        self.continue_btn.setVisible(False)
        self.end_btn.setVisible(False)
    
    def back_to_login(self):
        """Return to login screen"""
        try:
            # Launch login system
            login_path = os.path.join(os.path.dirname(__file__), "..", "..", "LoginSystem", "taikhoan", "main.py")
            if os.path.exists(login_path):
                subprocess.Popen([sys.executable, login_path])
                
            # Close current window
            self.close()
            
        except Exception as e:
            print(f"Error returning to login: {str(e)}")
            QMessageBox.critical(self, "Error", "Failed to return to login system")
    
    def update_camera_feed(self, frame):
        """Update camera feed with the received frame"""
        # Convert to Qt format
        rgb_frame = frame
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        scaled_image = qt_image.scaled(self.camera_label.width(), self.camera_label.height(), 
                                     Qt.AspectRatioMode.KeepAspectRatio)
        self.camera_label.setPixmap(QPixmap.fromImage(scaled_image))
    
    def handle_face_detected(self, data):
        """Handle when a face is detected and recognized"""
        student_key = f"{data['name']}_{data['id']}"
        already_checked_in = student_key in self.session_check_ins
        
        # Record attendance only if not already checked in during this session
        if not already_checked_in:
            self.record_attendance(data["name"], data["id"])
            self.session_check_ins.add(student_key)
            status_text = "✓ Successfully checked in"
            status_color = "#00c853"  # Green
        else:
            status_text = "✓ Already checked in this session"
            status_color = "#ff9800"  # Orange
        
        # Enable continue button
        self.continue_btn.setEnabled(True)
        
        # Update labels
        self.name_value.setText(data["name"])
        self.id_value.setText(data["id"])
        self.time_value.setText(datetime.now().strftime("%H:%M:%S"))
        self.status_message.setText(status_text)
        self.status_message.setStyleSheet(f"color: {status_color}; font-size: 16px; font-weight: bold;")
        self.status_label.setText(f"Face recognized: {data['name']}")
        self.status_label.setStyleSheet("color: #00c853; font-size: 16px;")
        
        # Update student photo
        for student in self.student_data:
            if student["id"] == data["id"]:
                try:
                    pixmap = QPixmap(student["image_path"])
                    self.student_photo.setPixmap(pixmap.scaled(
                        self.student_photo.width(),
                        self.student_photo.height(),
                        Qt.AspectRatioMode.KeepAspectRatio
                    ))
                except Exception as e:
                    print(f"Error loading student photo: {e}")
                    self.student_photo.setText("Photo N/A")
                break
    
    def update_ui(self):
        """Update UI elements that need regular refreshing"""
        # Update datetime
        current_time = datetime.now()
        self.datetime_label.setText(current_time.strftime("%d/%m/%Y %H:%M:%S"))
    
    def record_attendance(self, name, student_id):
        """Record attendance to history"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        # Create record
        record = {
            "name": name,
            "student_id": student_id,
            "date": date_str,
            "time": time_str
        }
        
        # Add to history
        self.attendance_history.append(record)
        
        # Save to JSON file
        self.save_attendance_history()
        
        # Update history table
        self.update_history_table()
    
    def load_attendance_history(self):
        """Tải lịch sử điểm danh từ tệp JSON trong thư mục data"""
        self.ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance_history.json")
        
        print(f"Đang tải lịch sử điểm danh từ: {self.ATTENDANCE_FILE}")
        
        # Đảm bảo thư mục data tồn tại
        os.makedirs(DATA_DIR, exist_ok=True)
        
        if os.path.exists(self.ATTENDANCE_FILE):
            try:
                with open(self.ATTENDANCE_FILE, "r", encoding='utf-8') as f:
                    self.attendance_history = json.load(f)
                    print(f"Đã tải {len(self.attendance_history)} bản ghi điểm danh")
                    self.update_history_table()
            except Exception as e:
                print(f"Lỗi khi tải lịch sử điểm danh: {str(e)}")
                self.attendance_history = []
        else:
            # Tạo tệp JSON rỗng nếu chưa tồn tại
            try:
                with open(self.ATTENDANCE_FILE, "w", encoding='utf-8') as f:
                    json.dump([], f)
                print(f"Đã tạo tệp lịch sử điểm danh mới tại: {self.ATTENDANCE_FILE}")
                self.attendance_history = []
            except Exception as e:
                print(f"Lỗi khi tạo tệp lịch sử điểm danh: {str(e)}")
                self.attendance_history = []
    
    def save_attendance_history(self):
        """Lưu lịch sử điểm danh vào tệp JSON trong thư mục data"""
        try:
            # Đảm bảo thư mục data tồn tại
            os.makedirs(DATA_DIR, exist_ok=True)
            
            # Tải các bản ghi hiện có
            existing_records = []
            if os.path.exists(self.ATTENDANCE_FILE):
                with open(self.ATTENDANCE_FILE, "r", encoding='utf-8') as f:
                    try:
                        existing_records = json.load(f)
                    except json.JSONDecodeError:
                        existing_records = []
            
            # Lấy các bản ghi mới
            existing_keys = {f"{r['student_id']}_{r['date']}_{r['time']}" for r in existing_records}
            new_records = [
                record for record in self.attendance_history 
                if f"{record['student_id']}_{record['date']}_{record['time']}" not in existing_keys
            ]
            
            # Kết hợp các bản ghi hiện có và mới
            all_records = existing_records + new_records
            
            # Lưu tất cả bản ghi vào tệp JSON
            with open(self.ATTENDANCE_FILE, "w", encoding='utf-8') as f:
                json.dump(all_records, f, indent=4, ensure_ascii=False)
            
            print(f"Đã thêm {len(new_records)} bản ghi điểm danh mới vào {self.ATTENDANCE_FILE}")
            
            # Cập nhật lịch sử điểm danh
            self.attendance_history = all_records
            
        except Exception as e:
            print(f"Lỗi khi lưu điểm danh: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu điểm danh: {str(e)}")
    
    def update_history_table(self):
        """Update the attendance history table"""
        # Clear table
        self.history_table.setRowCount(0)
        
        # Sort history by date and time (newest first)
        sorted_history = sorted(
            self.attendance_history, 
            key=lambda x: (x["date"], x["time"]),
            reverse=True
        )
        
        # Add rows
        for row, record in enumerate(sorted_history):
            self.history_table.insertRow(row)
            self.history_table.setItem(row, 0, QTableWidgetItem(record["name"]))
            self.history_table.setItem(row, 1, QTableWidgetItem(record["student_id"]))
            self.history_table.setItem(row, 2, QTableWidgetItem(record["date"]))
            self.history_table.setItem(row, 3, QTableWidgetItem(record["time"]))
    
    def closeEvent(self, event):
        """Handle close event"""
        # Stop all webcams if running
        if hasattr(self, 'face_recognition_webcam'):
            self.face_recognition_webcam.stop()
        if hasattr(self, 'second_webcam'):
            self.second_webcam.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AttendanceSystem()
    window.show()
    sys.exit(app.exec())