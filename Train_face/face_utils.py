import cv2
import numpy as np
import os
import pickle

class FaceRecognizer:
    def __init__(self, model_path='model/face_model.yml', label_path='model/label_encoder.pkl'):
        self.model_path = model_path
        self.label_path = label_path
        self.recognizer = None
        self.label_encoder = None
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
    def load_model(self):
        """Load trained model and label encoder"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.label_path):
                self.recognizer = cv2.face.LBPHFaceRecognizer_create()
                self.recognizer.read(self.model_path)
                
                with open(self.label_path, 'rb') as f:
                    self.label_encoder = pickle.load(f)
                
                print(f"✅ Model loaded: {len(self.label_encoder)} students")
                return True
            else:
                print("❌ Model files not found")
                return False
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False
    
    def detect_faces(self, image):
        """Detect faces in an image - SIMPLE"""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # VERY SIMPLE - just equalize histogram
        gray = cv2.equalizeHist(gray)
        
        # Face detection with relaxed parameters
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=3,  # Reduced for better detection
            minSize=(60, 60)  # Smaller minimum size
        )
        return faces, gray
    
    def preprocess_face(self, face_roi):
        """Preprocess face ROI - MUST BE SIMPLE"""
        # 1. Resize to 100x100
        face_roi = cv2.resize(face_roi, (100, 100))
        
        # 2. Equalize histogram
        face_roi = cv2.equalizeHist(face_roi)
        
        # 3. Apply mild Gaussian blur to reduce noise
        face_roi = cv2.GaussianBlur(face_roi, (3, 3), 0)
        
        return face_roi
    
    def recognize_face(self, image, debug=False):
        """Recognize face in image - SIMPLE"""
        if self.recognizer is None or self.label_encoder is None:
            if not self.load_model():
                return None, 0
        
        faces, gray = self.detect_faces(image)
        
        if len(faces) == 0:
            if debug:
                print("❌ No faces detected")
            return None, 0
        
        # Get the first face
        (x, y, w, h) = faces[0]
        
        # Get face ROI from the grayscale image
        face_roi = gray[y:y+h, x:x+w]
        
        # Preprocess
        face_roi = self.preprocess_face(face_roi)
        
        # Predict
        try:
            label, confidence = self.recognizer.predict(face_roi)
            
            if debug:
                print(f"Raw confidence: {confidence}")
            
            # LBPH: Lower confidence = better match
            confidence_percent = max(0, 100 - min(confidence, 100))
            
            # Get student name from label
            student_name = self.label_encoder.get(label, None)
            
            # LOWER THRESHOLD for testing
            if confidence_percent > 40 and student_name:  # Changed from 50 to 40
                return student_name, confidence_percent
            else:
                if debug:
                    print(f"❌ Below threshold ({confidence_percent:.1f}% < 40%) or unknown label")
                return None, confidence_percent
                
        except Exception as e:
            if debug:
                print(f"❌ Prediction error: {e}")
            return None, 0