from flask import Flask, render_template, request, jsonify, send_from_directory
import cv2
import numpy as np
import base64
import json
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

app = Flask(__name__, 
           static_folder='static',
           static_url_path='/static')
app.secret_key = 'face-test-secret-2024'
app.config['SESSION_COOKIE_NAME'] = 'face_test_session'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Database configuration
# Database configuration - use environment variables for Docker
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'face_recognition_db'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', '2510'),
    'host': os.getenv('DB_HOST', 'db'),  # 'db' is the service name in docker-compose
    'port': os.getenv('DB_PORT', '5432')
}

@contextmanager
def get_db_connection():
    """Database connection context manager"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_db_cursor():
    """Database cursor context manager"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            conn.commit()
        finally:
            cursor.close()

def log_recognition(test_type, student_name, confidence):
    """Log recognition result to database"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO recognition_history (test_type, student_name, confidence)
                VALUES (%s, %s, %s)
                """,
                (test_type, student_name, confidence)
            )
        return True
    except Exception as e:
        print(f"Error logging to database: {e}")
        return False

def get_recognition_history(limit=50, offset=0):
    """Get recognition history from database"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    id,
                    timestamp,
                    test_type,
                    student_name,
                    confidence,
                    CASE 
                        WHEN confidence >= 70 THEN 'High'
                        WHEN confidence >= 40 THEN 'Medium'
                        ELSE 'Low'
                    END as confidence_level
                FROM recognition_history
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []

def get_analytics_data(days=7):
    """Get analytics data for charts"""
    try:
        with get_db_cursor() as cursor:
            # Daily recognition counts
            cursor.execute(
                """
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM recognition_history
                WHERE timestamp >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(timestamp)
                ORDER BY date
                """,
                (days,)
            )
            daily_data = cursor.fetchall()
            
            # Confidence distribution
            cursor.execute(
                """
                SELECT 
                    CASE 
                        WHEN confidence >= 70 THEN 'High (70-100%)'
                        WHEN confidence >= 40 THEN 'Medium (40-69%)'
                        ELSE 'Low (0-39%)'
                    END as confidence_range,
                    COUNT(*) as count
                FROM recognition_history
                WHERE timestamp >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY confidence_range
                ORDER BY confidence_range
                """,
                (days,)
            )
            confidence_distribution = cursor.fetchall()
            
            # Test type distribution
            cursor.execute(
                """
                SELECT 
                    test_type,
                    COUNT(*) as count
                FROM recognition_history
                WHERE timestamp >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY test_type
                """,
                (days,)
            )
            test_type_distribution = cursor.fetchall()
            
            return {
                'daily_data': daily_data,
                'confidence_distribution': confidence_distribution,
                'test_type_distribution': test_type_distribution
            }
    except Exception as e:
        print(f"Error fetching analytics: {e}")
        return {}

def get_statistics():
    """Get overall statistics"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total_tests FROM recognition_history")
            total_tests = cursor.fetchone()['total_tests']
            
            cursor.execute("SELECT COUNT(DISTINCT student_name) as unique_students FROM recognition_history WHERE student_name IS NOT NULL AND student_name != 'Unknown'")
            unique_students = cursor.fetchone()['unique_students']
            
            cursor.execute("SELECT AVG(confidence) as avg_confidence FROM recognition_history")
            avg_confidence = cursor.fetchone()['avg_confidence'] or 0
            
            cursor.execute("SELECT COUNT(*) as today_tests FROM recognition_history WHERE DATE(timestamp) = CURRENT_DATE")
            today_tests = cursor.fetchone()['today_tests']
            
            return {
                'total_tests': total_tests,
                'unique_students': unique_students,
                'avg_confidence': round(float(avg_confidence), 2) if avg_confidence else 0,
                'today_tests': today_tests
            }
    except Exception as e:
        print(f"Error fetching statistics: {e}")
        return {}

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
    """Render the main dashboard"""
    return render_template('test_model.html')

@app.route('/dashboard')
def dashboard():
    """Render the analytics dashboard"""
    return render_template('dashboard.html')

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
        test_type = request.args.get('type', 'Upload Image Test')
        
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
        
        # Log to database only for upload test (triggered by button)
        if test_type == 'Upload Image Test':
            log_recognition('Upload Image Test', recognized_name, confidence)
        
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
    """Capture face image for verification and log to database"""
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
        
        # Detect and recognize face
        if not face_recognition_ready or face_recognizer is None:
            return jsonify({'success': False, 'message': 'Face recognition model not loaded'}), 500
        
        faces, gray = face_recognizer.detect_faces(image)
        
        face_count = len(faces)
        has_face = face_count > 0
        
        # Calculate confidence
        confidence = 0
        recognized_name = 'Unknown'
        
        if has_face:
            # Try to recognize the face
            recognized_name, confidence = face_recognizer.recognize_face(image)
            
            # Log to database (Live Camera Test triggered by Capture Face button)
            log_recognition('Live Camera Test', recognized_name, confidence)
            
            if confidence is None:
                confidence = 0
            else:
                confidence = round(float(confidence), 2)
        else:
            # Log failed detection
            log_recognition('Live Camera Test', 'No face detected', 0)
        
        return jsonify({
            'success': True,
            'face_detected': has_face,
            'face_count': face_count,
            'recognized_name': recognized_name,
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

@app.route('/api/get-recognition-history')
def get_history():
    """Get recognition history from database"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        history = get_recognition_history(limit, offset)
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        print(f"Error getting history: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/get-analytics')
def get_analytics():
    """Get analytics data for charts"""
    try:
        days = request.args.get('days', 7, type=int)
        analytics_data = get_analytics_data(days)
        
        return jsonify({
            'success': True,
            'analytics': analytics_data,
            'statistics': get_statistics()
        })
    except Exception as e:
        print(f"Error getting analytics: {e}")
        return jsonify({'success': False, 'message': str(e)})
    

@app.route('/api/get-confidence-trend')
def get_confidence_trend():
    """Get confidence trend data for chart"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    timestamp,
                    student_name,
                    confidence
                FROM recognition_history
                ORDER BY timestamp DESC
                LIMIT 50
                """
            )
            history = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'history': history,
                'count': len(history)
            })
    except Exception as e:
        print(f"Error getting confidence trend: {e}")
        return jsonify({'success': False, 'message': str(e)})
    

@app.route('/api/get-statistics')
def get_stats():
    """Get overall statistics"""
    try:
        stats = get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return jsonify({'success': False, 'message': str(e)})

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    # Print directory structure for debugging
    print("Current directory:", os.getcwd())
    print("Templates exists:", os.path.exists('templates'))
    print("Static exists:", os.path.exists('static'))
    
    if os.path.exists('templates'):
        print("Files in templates:", os.listdir('templates'))
    if os.path.exists('static'):
        print("Files in static:", os.listdir('static'))
    
    # For Docker, use 0.0.0.0 to allow external connections
    app.run(host='0.0.0.0', port=5000, debug=False)  # debug=False for production