import cv2
import numpy as np
import os
import pickle
import time
import random
import shutil

def generate_in_memory_training_data(student_path, student_name, min_images=100):
    """
    IN-MEMORY version - creates training data without touching files
    Returns: List of preprocessed face images for training
    """
    # Get ONLY original images (no dup_ files)
    image_files = [f for f in os.listdir(student_path) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        print(f"⚠️ No images for {student_name}")
        return []
    
    original_count = len(image_files)
    print(f"  {student_name}: {original_count} original images")
    
    # Load all original images
    loaded_images = []
    for img_file in image_files:
        img_path = os.path.join(student_path, img_file)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            loaded_images.append(img)
    
    if not loaded_images:
        return []
    
    # If we already have enough, use them (shuffled)
    if original_count >= min_images:
        print(f"  → Using {min_images} original images (shuffled)")
        random.shuffle(loaded_images)
        return loaded_images[:min_images]
    
    # We need to duplicate in memory
    needed = min_images - original_count
    print(f"  → Creating {needed} in-memory duplicates")
    
    # Start with all originals
    training_images = loaded_images.copy()
    
    # Add random duplicates until we reach min_images
    while len(training_images) < min_images:
        random_img = random.choice(loaded_images)
        training_images.append(random_img.copy())
    
    print(f"  → Generated {len(training_images)} images in memory")
    return training_images

def apply_virtual_angles(face_roi):
    """
    Create simple angle variations from a single face for better training
    Returns: List of face images with different virtual angles
    """
    angled_faces = [face_roi.copy()]  # Original as first
    
    height, width = face_roi.shape[:2]
    
    # Define source points (original face rectangle)
    src_points = np.float32([
        [0, 0],
        [width-1, 0],
        [0, height-1],
        [width-1, height-1]
    ])
    
    # Create simple angle variations (these simulate slight head movements)
    angle_variations = [
        # Slight left turn (perspective shift)
        [(3, 3), (width-6, 0), (3, height-3), (width-6, height-1)],
        
        # Slight right turn
        [(0, 0), (width-3, 3), (0, height-1), (width-3, height-6)],
        
        # Slight upward tilt
        [(0, 5), (width-1, 0), (0, height-1), (width-1, height-5)],
        
        # Slight downward tilt
        [(0, 0), (width-1, 5), (0, height-5), (width-1, height-1)]
    ]
    
    # Apply each variation
    for i, variation in enumerate(angle_variations[:2]):  # Use only 2 variations for simplicity
        dst_points = np.float32(variation)
        
        # Calculate perspective transform
        M = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Apply perspective transformation
        try:
            angled_face = cv2.warpPerspective(face_roi, M, (width, height))
            
            # Check if the resulting image is valid (not too dark)
            if np.mean(angled_face) > 20:
                angled_faces.append(angled_face)
        except:
            continue  # Skip if transformation fails
    
    # Always add horizontally flipped version of the original
    flipped = cv2.flip(face_roi, 1)
    angled_faces.append(flipped)
    
    # Return up to 4 variations (original + up to 3)
    return angled_faces[:4]

def train_face_model(data_path='data'):
    """
    Train face recognition model with in-memory duplication
    NO changes to original data folder
    """
    print("="*60)
    print("FACE RECOGNITION TRAINING")
    print(f"Data path: {data_path}")
    print("="*60)
    print("Features:")
    print("• Ensures 100 images per person (in-memory duplicates)")
    print("• Adds angle variations for better recognition")
    print("• Keeps data folder clean - no duplicate files")
    print("• Simple and consistent preprocessing")
    print("="*60)
    
    # Use same LBPH parameters as before
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1,
        neighbors=8,
        grid_x=6,
        grid_y=6,
        threshold=75.0
    )
    
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    faces_list = []
    labels_list = []
    label_dict = {}
    current_label = 0
    
    # Get students
    student_folders = sorted([f for f in os.listdir(data_path) 
                             if os.path.isdir(os.path.join(data_path, f))])
    
    if not student_folders:
        print("❌ No students found in data folder!")
        return False
    
    print(f"\nFound {len(student_folders)} students")
    print("="*60)
    
    start_time = time.time()
    total_original_images = 0
    total_training_samples = 0
    
    for student_name in student_folders:
        student_path = os.path.join(data_path, student_name)
        label_dict[current_label] = student_name
        
        print(f"\n[{current_label+1}/{len(student_folders)}] Processing: {student_name}")
        print("-" * 40)
        
        # Generate 100 images in memory
        image_list = generate_in_memory_training_data(student_path, student_name, min_images=100)
        
        if not image_list:
            print(f"  ⚠️ Skipping {student_name} - no valid images")
            current_label += 1
            continue
        
        # Count original images
        original_images = [f for f in os.listdir(student_path) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        total_original_images += len(original_images)
        
        processed_images = 0
        samples_for_student = 0
        
        # Process each image
        for img_idx, image in enumerate(image_list):
            # SIMPLE preprocessing (EXACTLY like recognition)
            # 1. Equalize histogram
            gray = cv2.equalizeHist(image)
            
            # 2. Detect face with same parameters
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=3,  # Same as recognition
                minSize=(60, 60)  # Same as recognition
            )
            
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                face_roi = gray[y:y+h, x:x+w]
                
                # Preprocess EXACTLY like recognition
                # 1. Resize to 100x100
                face_roi = cv2.resize(face_roi, (100, 100))
                
                # 2. Equalize histogram (again, to match recognition)
                face_roi = cv2.equalizeHist(face_roi)
                
                # 3. Apply mild Gaussian blur
                face_roi = cv2.GaussianBlur(face_roi, (3, 3), 0)
                
                # Create angle variations for better training
                angled_faces = apply_virtual_angles(face_roi)
                
                # Add all angle variations to training data
                for angle_face in angled_faces:
                    faces_list.append(angle_face)
                    labels_list.append(current_label)
                    samples_for_student += 1
                    total_training_samples += 1
                
                processed_images += 1
                
                # Show progress every 20 images
                if processed_images % 20 == 0:
                    print(f"    Processed {processed_images}/100 images")
        
        print(f"  ✅ {student_name}: {len(original_images)} originals → {samples_for_student} training samples")
        current_label += 1
    
    if len(faces_list) == 0:
        print("\n❌ No faces found in any image!")
        return False
    
    # Training statistics
    print("\n" + "="*60)
    print("TRAINING DATA SUMMARY")
    print("="*60)
    print(f"Total students: {len(label_dict)}")
    print(f"Total original images: {total_original_images}")
    print(f"Total training samples: {total_training_samples}")
    print(f"Average samples per student: {total_training_samples//len(label_dict)}")
    
    # Convert to numpy arrays
    faces_array = np.array(faces_list)
    labels_array = np.array(labels_list)
    
    # Optional: Shuffle the data for better training
    if len(faces_array) > 0:
        indices = np.random.permutation(len(faces_array))
        faces_array = faces_array[indices]
        labels_array = labels_array[indices]
    
    # Train the model
    print("\n" + "="*60)
    print("TRAINING MODEL...")
    print("="*60)
    
    recognizer.train(faces_array, labels_array)
    
    # Save model
    os.makedirs('model', exist_ok=True)
    model_path = 'model/face_model.yml'
    recognizer.write(model_path)
    
    # Save labels
    label_path = 'model/label_encoder.pkl'
    with open(label_path, 'wb') as f:
        pickle.dump(label_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    # Training complete
    training_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("✅ TRAINING COMPLETE!")
    print("="*60)
    print(f"⏱️  Training time: {training_time:.1f} seconds")
    print(f"👤 Students trained: {len(label_dict)}")
    print(f"📸 Training samples used: {len(faces_array)}")
    print(f"💾 Model saved to: {model_path}")
    
    # Check model size
    if os.path.exists(model_path):
        model_size = os.path.getsize(model_path) / (1024 * 1024)
        print(f"📦 Model size: {model_size:.1f} MB")
    
    # Quick self-test
    print("\n🧪 Performing quick self-test...")
    quick_test(faces_array[:5], labels_array[:5], recognizer, label_dict)
    
    return True

def quick_test(faces, labels, recognizer, label_dict):
    """Quick test on training data itself"""
    correct = 0
    print("  Testing 5 random training samples:")
    
    for i in range(min(5, len(faces))):
        label, confidence = recognizer.predict(faces[i])
        confidence_percent = max(0, 100 - min(confidence, 100))
        
        if label == labels[i] and confidence_percent > 50:
            correct += 1
            status = "✓"
        else:
            status = "✗"
        
        actual_name = label_dict.get(labels[i], 'Unknown')
        predicted_name = label_dict.get(label, 'Unknown')
        
        print(f"    {status} {actual_name} -> {predicted_name}: {confidence_percent:.1f}%")
    
    if correct >= 3:
        print("  ✅ Model is learning correctly")
    else:
        print("  ⚠️  Model may need more training data")

def test_on_existing_images():
    """Test using only original images from the data folder"""
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read('model/face_model.yml')
        
        with open('model/label_encoder.pkl', 'rb') as f:
            label_dict = pickle.load(f)
        
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        correct = 0
        total = 0
        
        print(f"\n📊 Testing on ORIGINAL images only...")
        print("-" * 40)
        
        for label, student_name in label_dict.items():
            student_path = os.path.join('data', student_name)
            if not os.path.exists(student_path):
                continue
            
            # Only test on original images
            image_files = [f for f in os.listdir(student_path) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if not image_files:
                continue
            
            # Test with up to 3 random original images
            test_files = random.sample(image_files, min(3, len(image_files)))
            
            for img_file in test_files:
                img_path = os.path.join(student_path, img_file)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                
                if img is None:
                    continue
                
                # EXACTLY same preprocessing as training
                gray = cv2.equalizeHist(img)
                faces = face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(60, 60))
                
                if len(faces) > 0:
                    (x, y, w, h) = faces[0]
                    face_roi = gray[y:y+h, x:x+w]
                    face_roi = cv2.resize(face_roi, (100, 100))
                    face_roi = cv2.equalizeHist(face_roi)
                    face_roi = cv2.GaussianBlur(face_roi, (3, 3), 0)
                    
                    pred_label, confidence = recognizer.predict(face_roi)
                    confidence_percent = max(0, 100 - min(confidence, 100))
                    
                    if pred_label == label and confidence_percent > 40:
                        correct += 1
                        status = "✓"
                    else:
                        status = "✗"
                    
                    total += 1
                    print(f"  {status} {student_name}: {confidence_percent:.1f}%")
        
        if total > 0:
            accuracy = (correct / total) * 100
            print("-" * 40)
            print(f"📈 Accuracy on original images: {accuracy:.1f}% ({correct}/{total})")
            
            if accuracy < 60:
                print("\n💡 Suggestions to improve accuracy:")
                print("  1. Add more original images per person")
                print("  2. Ensure faces are clear and well-lit")
                print("  3. Retrain with current data")
            
            return accuracy
        return 0.0
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return 0.0

def check_data_status(data_path='data'):
    """Check how many images each student has"""
    print("\n📋 Data Status Check")
    print("="*60)
    
    student_folders = sorted([f for f in os.listdir(data_path) 
                             if os.path.isdir(os.path.join(data_path, f))])
    
    if not student_folders:
        print("No students found!")
        return
    
    print(f"Found {len(student_folders)} students")
    print("-" * 60)
    
    total_images = 0
    
    for student_name in student_folders:
        student_path = os.path.join(data_path, student_name)
        
        image_files = [f for f in os.listdir(student_path) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        count = len(image_files)
        total_images += count
        
        if count >= 100:
            status = "✅ Excellent"
        elif count >= 50:
            status = "👍 Good"
        elif count >= 20:
            status = "⚠️  Fair"
        elif count >= 10:
            status = "⚠️  Low"
        else:
            status = "❌ Very Low"
        
        print(f"{student_name}:")
        print(f"    {count} images - {status}")
    
    print("-" * 60)
    print(f"Total images across all students: {total_images}")
    print(f"Average images per student: {total_images//len(student_folders) if student_folders else 0}")

def main_menu():
    """Main menu for the training system"""
    while True:
        print("\n" + "="*60)
        print("FACE RECOGNITION TRAINING SYSTEM")
        print("="*60)
        print("1. Train model (in-memory, keeps data folder clean)")
        print("2. Test model on original images")
        print("3. Check data status")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            print("\n" + "="*60)
            print("STARTING TRAINING")
            print("="*60)
            print("This will:")
            print("• Use 100 images per student (in-memory duplicates)")
            print("• Add angle variations for better recognition")
            print("• Keep your data folder unchanged")
            print("• Train with consistent preprocessing")
            
            confirm = input("\nContinue? (y/n): ").strip().lower()
            if confirm != 'y':
                continue
            
            # Delete old model first
            if os.path.exists('model'):
                try:
                    shutil.rmtree('model')
                    print("Removed old model")
                except:
                    pass
            
            # Train fresh
            if train_face_model():
                print("\n" + "="*60)
                print("TESTING TRAINED MODEL")
                print("="*60)
                test_on_existing_images()
        
        elif choice == '2':
            if os.path.exists('model/face_model.yml'):
                test_on_existing_images()
            else:
                print("❌ Model not found. Please train first (option 1).")
        
        elif choice == '3':
            check_data_status()
        
        elif choice == '4':
            print("\nGoodbye! 👋")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-4.")

if __name__ == "__main__":
    main_menu()