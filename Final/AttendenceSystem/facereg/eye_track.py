import cv2
import numpy as np
import dlib
import time
from PyQt6.QtCore import QThread, pyqtSignal
from collections import deque
import random

class EyeTrackingWebcam(QThread):
    frame_ready = pyqtSignal(object)
    test_completed = pyqtSignal(bool)
    direction_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = True
        
        # Initialize webcam with better settings
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        
        # Add these new initializations
        self.direction_buffer = deque(maxlen=5)  # Buffer for smoothing directions
        self.gaze_threshold = 0.2
        
        # Enhanced face and landmark detection
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("/Users/ngochuynh/Downloads/FaceRecog_Nhom10/Final/AttendenceSystem/facereg/shape_predictor_68_face_landmarks.dat")
        
        # Simplified test parameters
        self.test_sequence = []
        self.current_direction = None
        self.direction_hold_time = 0
        self.required_hold_time = 2.0  # Seconds to hold each direction
        self.test_passed = False
        
        # Simple directions for testing
        self.directions = {
            'left': 'LEFT ⬅️',
            'right': 'RIGHT ➡️',
            'up': 'UP ⬆️',
            'down': 'DOWN ⬇️',
            'center': 'CENTER ⏺️'
        }
        
    def generate_test_sequence(self):
        """Generate a random 3-direction test sequence"""
        possible_directions = ['left', 'right', 'up', 'down']
        self.test_sequence = random.sample(possible_directions, 3)  # Pick 3 random directions
        print(f"Generated test sequence: {self.test_sequence}")
        self.current_direction = self.test_sequence.pop(0)
        self.direction_hold_time = time.time()
        return self.current_direction
    
    def get_eye_direction(self, eyes_landmarks, frame):
        """Enhanced eye direction detection using iris/pupil tracking"""
        if eyes_landmarks.size == 0:
            return None
            
        def extract_eye_region(eye_points):
            # Get eye region boundaries
            min_x = np.min(eye_points[:, 0])
            max_x = np.max(eye_points[:, 0])
            min_y = np.min(eye_points[:, 1])
            max_y = np.max(eye_points[:, 1])
            
            # Add padding
            padding = 5
            eye_region = frame[max(0, int(min_y-padding)):int(max_y+padding),
                            max(0, int(min_x-padding)):int(max_x+padding)]
            return eye_region, (min_x, min_y)
        
        # Get eye regions
        left_eye_points = eyes_landmarks[36:42]
        right_eye_points = eyes_landmarks[42:48]
        
        # Process each eye
        def process_eye(eye_region, origin):
            if eye_region.size == 0:
                return None
                
            # Convert to grayscale
            gray_eye = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
            
            # Apply filters to isolate pupil
            _, threshold = cv2.threshold(gray_eye, 35, 255, cv2.THRESH_BINARY_INV)
            kernel = np.ones((3, 3), np.uint8)
            threshold = cv2.erode(threshold, kernel, iterations=1)
            threshold = cv2.dilate(threshold, kernel, iterations=2)
            
            # Find contours
            contours, _ = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None
                
            # Get largest contour (likely the pupil)
            pupil_contour = max(contours, key=cv2.contourArea)
            
            # Calculate pupil center
            M = cv2.moments(pupil_contour)
            if M["m00"] == 0:
                return None
                
            pupil_x = int(M["m10"] / M["m00"]) + origin[0]
            pupil_y = int(M["m01"] / M["m00"]) + origin[1]
            
            return np.array([pupil_x, pupil_y])
        
        # Get eye centers and pupil positions
        left_eye_region, left_origin = extract_eye_region(left_eye_points)
        right_eye_region, right_origin = extract_eye_region(right_eye_points)
        
        left_pupil = process_eye(left_eye_region, left_origin)
        right_pupil = process_eye(right_eye_region, right_origin)
        
        if left_pupil is None or right_pupil is None:
            return None
        
        # Calculate eye centers
        left_eye_center = np.mean(left_eye_points, axis=0)
        right_eye_center = np.mean(right_eye_points, axis=0)
        
        # Calculate relative pupil positions
        left_rel = left_pupil - left_eye_center
        right_rel = right_pupil - right_eye_center
        
        # Normalize by eye width
        left_eye_width = np.linalg.norm(left_eye_points[3] - left_eye_points[0])
        right_eye_width = np.linalg.norm(right_eye_points[3] - right_eye_points[0])
        
        left_rel = left_rel / left_eye_width
        right_rel = right_rel / right_eye_width
        
        # Average both eyes with weights based on confidence
        rel_pos = (left_rel + right_rel) / 2
        
        # Apply Kalman filtering for smooth tracking
        if not hasattr(self, 'kalman'):
            self.kalman = cv2.KalmanFilter(4, 2)
            self.kalman.measurementMatrix = np.array([[1, 0, 0, 0],
                                                    [0, 1, 0, 0]], np.float32)
            self.kalman.transitionMatrix = np.array([[1, 0, 1, 0],
                                                [0, 1, 0, 1],
                                                [0, 0, 1, 0],
                                                [0, 0, 0, 1]], np.float32)
            self.kalman.processNoiseCov = np.array([[1,0,0,0],
                                                [0,1,0,0],
                                                [0,0,1,0],
                                                [0,0,0,1]], np.float32) * 0.03
                                                
        # Update Kalman filter
        prediction = self.kalman.predict()
        measurement = np.array([[np.float32(rel_pos[0])], [np.float32(rel_pos[1])]])
        self.kalman.correct(measurement)
        
        # Get filtered position
        filtered_pos = prediction[:2].flatten()
        
        return self.classify_direction(filtered_pos)

    def classify_direction(self, rel_pos):
        """Enhanced direction classification with adaptive thresholding"""
        x, y = rel_pos
        
        # Add to direction buffer for smoothing
        self.direction_buffer.append((x, y))
        
        # Calculate moving averages
        smooth_x = np.mean([d[0] for d in self.direction_buffer])
        smooth_y = np.mean([d[1] for d in self.direction_buffer])
        
        # Calculate standard deviation for adaptive thresholding
        std_x = np.std([d[0] for d in self.direction_buffer])
        std_y = np.std([d[1] for d in self.direction_buffer])
        
        # Adaptive thresholds
        threshold_x = max(self.gaze_threshold, std_x * 2)
        threshold_y = max(self.gaze_threshold, std_y * 2)
        
        # Hysteresis thresholding with confidence scoring
        confidence_x = abs(smooth_x) / threshold_x
        confidence_y = abs(smooth_y) / threshold_y
        
        if confidence_x > confidence_y:
            if abs(smooth_x) > threshold_x:
                return 'left' if smooth_x < 0 else 'right'
        else:
            if abs(smooth_y) > threshold_y:
                return 'up' if smooth_y < 0 else 'down'
                
        return 'center'
    
    def run(self):
        """Main processing loop"""
        if not self.test_sequence:
            self.generate_test_sequence()
        
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            # Mirror the frame for more intuitive feedback
            frame = cv2.flip(frame, 1)
            
            # Detect face and landmarks
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray)
            
            direction = None
            if len(faces) > 0:
                face = faces[0]  # Use the first detected face
                landmarks = self.predictor(gray, face)
                landmarks = np.array([[p.x, p.y] for p in landmarks.parts()])
                
                # Get current eye direction
                direction = self.get_eye_direction(landmarks, frame)
                self.draw_landmarks(frame, landmarks)
                
                # Check if direction matches and is held long enough
                if direction == self.current_direction:
                    if time.time() - self.direction_hold_time >= self.required_hold_time:
                        if self.test_sequence:
                            # Move to next direction
                            self.current_direction = self.test_sequence.pop(0)
                            self.direction_hold_time = time.time()
                            self.direction_changed.emit(self.current_direction)
                        else:
                            # Test completed successfully
                            self.test_passed = True
                            self.draw_success_message(frame)
                            self.test_completed.emit(True)
                            self.running = False
                            break
                else:
                    # Reset hold time if direction changes
                    self.direction_hold_time = time.time()
            
            # Draw the interface
            self.draw_interface(frame, direction)
            
            # Convert to RGB for Qt
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.frame_ready.emit(rgb_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    def draw_success_message(self, frame):
        """Draw success message when test is completed"""
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (w//4, h//3), (3*w//4, 2*h//3), (0, 0, 0), -1)
        cv2.rectangle(frame, (w//4, h//3), (3*w//4, 2*h//3), (0, 255, 0), 3)
        cv2.putText(frame, "Test Completed Successfully!", 
                    (w//4 + 20, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    def draw_interface(self, frame, current_direction):
        """Draw user interface with clear instructions"""
        h, w = frame.shape[:2]
        
        # Draw test progress
        remaining = len(self.test_sequence) + 1
        cv2.putText(frame, f"Test Progress: {4-remaining}/3", 
                    (w-200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
        # Display detected eye direction (using the parameter)
        if current_direction:
            cv2.putText(frame, f"Detected: {self.directions.get(current_direction, 'Unknown')}", 
                        (w-200, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw instruction box
        cv2.rectangle(frame, (30, 20), (w-30, 120), (0, 0, 0), -1)
        cv2.rectangle(frame, (30, 20), (w-30, 120), (0, 255, 0), 2)
        
        # Draw target direction with arrow
        instruction = f"Look {self.directions[self.current_direction]}"
        cv2.putText(frame, instruction, 
                    (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Draw progress bar
        if self.direction_hold_time:
            progress = min(1.0, (time.time() - self.direction_hold_time) / self.required_hold_time)
            bar_width = int((w-60) * progress)
            cv2.rectangle(frame, (30, 80), (30 + bar_width, 100), (0, 255, 0), -1)
            cv2.rectangle(frame, (30, 80), (w-30, 100), (255, 255, 255), 2)
            
            # Show hold time
            time_left = max(0, self.required_hold_time - (time.time() - self.direction_hold_time))
            cv2.putText(frame, f"Hold for: {time_left:.1f}s", 
                        (50, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    def draw_landmarks(self, frame, landmarks):
        """Draw facial landmarks and eye regions"""
        # Draw eye landmarks
        for n in range(36, 48):
            x = landmarks[n][0]
            y = landmarks[n][1]
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
        
        # Draw eye regions
        left_eye = landmarks[36:42]
        right_eye = landmarks[42:48]
        
        cv2.polylines(frame, [np.int32(left_eye)], True, (0, 255, 0), 1)
        cv2.polylines(frame, [np.int32(right_eye)], True, (0, 255, 0), 1)
    
    def stop(self):
        """Stop the thread and release resources"""
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.wait()