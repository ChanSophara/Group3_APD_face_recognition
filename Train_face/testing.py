import cv2
import numpy as np
from face_utils import FaceRecognizer

def test_camera_recognition():
    """Test face recognition from camera"""
    recognizer = FaceRecognizer()
    
    # Load model
    if not recognizer.load_model():
        print("Model not found. Please train the model first.")
        return
    
    print("Model loaded successfully!")
    print("Starting camera... Press 'q' to quit")
    
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Make a copy for display
        display = frame.copy()
        
        # Recognize face
        student_name, confidence = recognizer.recognize_face(frame)
        
        # Draw results
        if student_name:
            text = f"{student_name} ({confidence:.1f}%)"
            color = (0, 255, 0)  # Green
        else:
            text = "Unknown"
            color = (0, 0, 255)  # Red
        
        cv2.putText(display, text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        # Detect and draw face rectangle
        faces, gray = recognizer.detect_faces(frame)
        for (x, y, w, h) in faces:
            cv2.rectangle(display, (x, y), (x+w, y+h), color, 2)
        
        cv2.imshow('Face Recognition Test', display)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def test_image_recognition(image_path):
    """Test face recognition on a single image"""
    recognizer = FaceRecognizer()
    
    if not recognizer.load_model():
        print("Model not found. Please train the model first.")
        return
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot read image: {image_path}")
        return
    
    student_name, confidence = recognizer.recognize_face(image)
    
    if student_name:
        print(f"Recognized: {student_name}")
        print(f"Confidence: {confidence:.1f}%")
        
        # Draw result on image
        faces, gray = recognizer.detect_faces(image)
        for (x, y, w, h) in faces:
            cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        cv2.putText(image, f"{student_name} ({confidence:.1f}%)", 
                   (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        cv2.imshow('Result', image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("No face recognized")
        if confidence > 0:
            print(f"Confidence: {confidence:.1f}%")


if __name__ == "__main__":
    # Test with camera
    test_camera_recognition()
    
    # Test with single image
    # test_image_recognition("test_image.jpg")