from flask import Flask, render_template, request, jsonify, send_from_directory
import cv2
import numpy as np
import base64
import json
import os
from datetime import datetime

app = Flask(__name__, 
           static_folder='static',  # Specify static folder
           static_url_path='/static')  # URL path for static files
app.secret_key = 'face-test-secret-2024'
app.config['SESSION_COOKIE_NAME'] = 'face_test_session'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Initialize face recognizer
try:
    from face_recognition_utils import init_face_recognition, face_recognizer
    face_recognition_ready = init_face_recognition()
    print(f"Face recognition ready: {face_recognition_ready}")
except Exception as e:
    print(f"Error initializing face recognition: {e}")
    face_recognition_ready = False
    face_recognizer = None

@app.route('/')
def index():
    """Render the test model page"""
    return render_template('test_model.html')

# Serve static files explicitly (optional but good practice)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/api/detect-faces-with-boxes', methods=['POST'])
def detect_faces_with_boxes():
    """Detect faces and draw bounding boxes with recognition"""
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        if not face_recognition_ready:
            return jsonify({'success': False, 'message': 'Face recognition system not ready'}), 500
        
        # Decode base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'success': False, 'message': 'Invalid image'}), 400
        
        # Recognize face with bounding boxes
        recognized_name, confidence, processed_image = face_recognizer.recognize_face_with_box(image)
        
        # Convert processed image back to base64
        _, buffer = cv2.imencode('.jpg', processed_image)
        processed_image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'recognized_name': recognized_name or 'Unknown',
            'confidence': round(float(confidence), 2) if confidence else 0,
            'processed_image': f'data:image/jpeg;base64,{processed_image_base64}',
            'has_face': recognized_name is not None
        })
        
    except Exception as e:
        print(f"Face detection with boxes error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/test-face-recognition', methods=['POST'])
def test_face_recognition():
    """Test face recognition with camera or uploaded image"""
    try:
        # Check if it's file upload or base64 image
        if 'image' in request.files:
            # File upload
            file = request.files['image']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No selected file'}), 400
            
            # Read image file
            image_data = file.read()
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif 'image' in request.json:
            # Base64 image
            image_data = request.json['image'].split(',')[1]
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        if image is None:
            return jsonify({'success': False, 'message': 'Invalid image'}), 400
        
        # Recognize face
        if not face_recognition_ready or face_recognizer is None:
            return jsonify({'success': False, 'message': 'Face recognition model not loaded'}), 500
        
        recognized_name, confidence = face_recognizer.recognize_face(image)
        
        return jsonify({
            'success': True,
            'recognized_name': recognized_name or 'Unknown',
            'confidence': round(float(confidence), 2) if confidence else 0,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Face recognition test error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/capture-face', methods=['POST'])
def capture_face():
    """Capture face image for verification"""
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        # Decode base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Convert to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'success': False, 'message': 'Invalid image'}), 400
        
        # Detect face
        if not face_recognition_ready or face_recognizer is None:
            return jsonify({'success': False, 'message': 'Face recognition model not loaded'}), 500
        
        faces, gray = face_recognizer.detect_faces(image)
        
        face_count = len(faces)
        has_face = face_count > 0
        
        # Calculate confidence (simplified)
        confidence = 0
        if has_face:
            # Use face size as confidence indicator
            (x, y, w, h) = faces[0]
            face_area = w * h
            img_area = image.shape[0] * image.shape[1]
            confidence = min(100, int((face_area / img_area) * 300))
        
        return jsonify({
            'success': True,
            'face_detected': has_face,
            'face_count': face_count,
            'confidence': confidence
        })
        
    except Exception as e:
        print(f"Capture face error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/check-model-status')
def check_model_status():
    """Check if face recognition model is loaded"""
    return jsonify({
        'success': True,
        'model_loaded': face_recognition_ready,
        'students_count': len(face_recognizer.label_encoder) if face_recognizer and face_recognizer.label_encoder else 0
    })

@app.route('/api/get-all-students')
def get_all_students():
    """Get list of all students in the model"""
    try:
        if face_recognizer and face_recognizer.label_encoder:
            students = list(face_recognizer.label_encoder.values())
            return jsonify({
                'success': True,
                'students': students,
                'count': len(students)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Model not loaded'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # Print directory structure for debugging
    print("Current directory:", os.getcwd())
    print("Templates exists:", os.path.exists('templates'))
    print("Static exists:", os.path.exists('static'))
    
    if os.path.exists('templates'):
        print("Files in templates:", os.listdir('templates'))
    if os.path.exists('static'):
        print("Files in static:", os.listdir('static'))
    
    app.run(debug=True, port=5005, host='0.0.0.0')