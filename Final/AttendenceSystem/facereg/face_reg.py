import cv2
import numpy as np
import face_recognition
from PyQt6.QtCore import QThread, pyqtSignal

class FaceRecognitionWebcam(QThread):
    frame_ready = pyqtSignal(object)
    face_detected = pyqtSignal(dict)
    no_face_detected = pyqtSignal()
    
    def __init__(self, student_data):
        super().__init__()
        self.running = True
        
        # Load and prepare student data for face recognition
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        
        print("Loading student face data...")
        for student in student_data:
            try:
                image = face_recognition.load_image_file(student["image_path"])
                encoding = face_recognition.face_encodings(image)[0]
                self.known_face_encodings.append(encoding)
                self.known_face_names.append(student["name"])
                self.known_student_ids.append(student["id"])
                print(f"Loaded: {student['name']}")
            except Exception as e:
                print(f"Error loading {student['name']}: {e}")
                
        # Initialize webcam
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 1280)  # Width
        self.cap.set(4, 720)   # Height
        
        # Face recognition parameters
        self.recognition_cooldown = 0  # To prevent too frequent recognitions
        
    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            # Create a copy of the frame for processing
            process_frame = frame.copy()
            
            # Face recognition processing
            small_frame = cv2.resize(process_frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            # Process faces if found
            if face_locations and self.recognition_cooldown <= 0:
                # Scale back face locations to original size
                full_size_face_locations = [(top*4, right*4, bottom*4, left*4) 
                                         for (top, right, bottom, left) in face_locations]
                
                # Draw rectangles for faces
                for (top, right, bottom, left) in full_size_face_locations:
                    # Draw corner lines instead of full rectangle for better visual
                    color = (255, 153, 51)  # Orange color
                    thickness = 2
                    line_length = 20
                    
                    # Top-left
                    cv2.line(process_frame, (left, top), (left + line_length, top), color, thickness)
                    cv2.line(process_frame, (left, top), (left, top + line_length), color, thickness)
                    
                    # Top-right
                    cv2.line(process_frame, (right, top), (right - line_length, top), color, thickness)
                    cv2.line(process_frame, (right, top), (right, top + line_length), color, thickness)
                    
                    # Bottom-left
                    cv2.line(process_frame, (left, bottom), (left + line_length, bottom), color, thickness)
                    cv2.line(process_frame, (left, bottom), (left, bottom - line_length), color, thickness)
                    
                    # Bottom-right
                    cv2.line(process_frame, (right, bottom), (right - line_length, bottom), color, thickness)
                    cv2.line(process_frame, (right, bottom), (right, bottom - line_length), color, thickness)
                
                # Get face encodings and attempt recognition
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                if face_encodings:
                    # Use the first face detected
                    face_encoding = face_encodings[0]
                    
                    # Compare with known faces
                    distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    
                    if len(distances) > 0:
                        best_match_index = np.argmin(distances)
                        
                        # If face is recognized with high confidence
                        if distances[best_match_index] < 0.45:
                            name_display = self.known_face_names[best_match_index]
                            id_display = self.known_student_ids[best_match_index]
                            
                            # Draw recognized label
                            cv2.rectangle(process_frame, 
                                       (left, bottom + 35), 
                                       (right, bottom), 
                                       (0, 200, 83), 
                                       cv2.FILLED)
                            cv2.putText(process_frame, 
                                     f"{name_display}",
                                     (left + 6, bottom + 25), 
                                     cv2.FONT_HERSHEY_DUPLEX, 
                                     0.8, 
                                     (255, 255, 255), 
                                     1)
                            
                            # Emit signal with recognition data
                            self.face_detected.emit({
                                "name": name_display,
                                "id": id_display
                            })
                            
                            # Set cooldown to avoid multiple rapid recognitions
                            self.recognition_cooldown = 30  # frames
                        else:
                            # Unknown face
                            cv2.rectangle(process_frame, 
                                       (left, bottom + 35), 
                                       (right, bottom), 
                                       (0, 0, 255), 
                                       cv2.FILLED)
                            cv2.putText(process_frame, 
                                     "Unknown",
                                     (left + 6, bottom + 25), 
                                     cv2.FONT_HERSHEY_DUPLEX, 
                                     0.8, 
                                     (255, 255, 255), 
                                     1)
            
            # Decrease cooldown counter
            if self.recognition_cooldown > 0:
                self.recognition_cooldown -= 1
            
            # Convert BGR to RGB for Qt
            rgb_frame = cv2.cvtColor(process_frame, cv2.COLOR_BGR2RGB)
            
            # Emit the processed frame
            self.frame_ready.emit(rgb_frame)
    
    def stop(self):
        """Stop the thread and release resources"""
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.wait()