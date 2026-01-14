// Test Model functionality with real-time bounding boxes and database integration
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    const faceOverlay = document.getElementById('faceOverlay');
    const processedImage = document.getElementById('processedImage');
    const faceInfo = document.getElementById('faceInfo');
    const faceInfoName = document.getElementById('faceInfoName');
    const faceInfoConfidence = document.getElementById('faceInfoConfidence');
    
    // Buttons
    const startCameraBtn = document.getElementById('startCamera');
    const stopCameraBtn = document.getElementById('stopCamera');
    const testFaceBtn = document.getElementById('testFace');
    const captureFaceBtn = document.getElementById('captureFace');
    
    // Upload elements
    const uploadArea = document.getElementById('uploadArea');
    const imageUpload = document.getElementById('imageUpload');
    const imagePreview = document.getElementById('imagePreview');
    const previewImage = document.getElementById('previewImage');
    const clearPreviewBtn = document.getElementById('clearPreview');
    const testUploadBtn = document.getElementById('testUpload');
    const detectFacesBtn = document.getElementById('detectFaces');
    
    // Results elements
    const cameraResults = document.getElementById('cameraResults');
    const uploadResults = document.getElementById('uploadResults');
    
    // Status elements
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const countText = document.getElementById('countText');
    const studentsList = document.getElementById('studentsList');
    const footerStatus = document.getElementById('footerStatus');
    const dbStatus = document.getElementById('dbStatus');
    const cameraStatus = document.getElementById('cameraStatus');
    
    // Modal elements
    const testResultModal = document.getElementById('testResultModal');
    const testResultIcon = document.getElementById('testResultIcon');
    const testResultTitle = document.getElementById('testResultTitle');
    const testResultMessage = document.getElementById('testResultMessage');
    const closeTestResult = document.getElementById('closeTestResult');
    const testAgainBtn = document.getElementById('testAgain');
    
    // Test Details Modal
    const testDetailsModal = document.getElementById('testDetailsModal');
    const closeDetails = document.getElementById('closeDetails');
    const closeDetailsBtn = document.getElementById('closeDetailsBtn');
    const viewInDashboard = document.getElementById('viewInDashboard');
    
    // State variables
    let currentStream = null;
    let isCameraOn = false;
    let detectionInterval = null;
    let modelStatus = 'checking';
    let studentCount = 0;
    let databaseConnected = false;
    
    // Initialize
    initializeApp();
    
    function initializeApp() {
        setupEventListeners();
        setupUploadArea();
        checkModelStatus();
        loadStudentsList();
        updateCameraStatus();
    }
    
    function setupEventListeners() {
        // Camera controls
        if (startCameraBtn) startCameraBtn.addEventListener('click', startCamera);
        if (stopCameraBtn) stopCameraBtn.addEventListener('click', stopCamera);
        if (testFaceBtn) testFaceBtn.addEventListener('click', testFaceRecognition);
        if (captureFaceBtn) captureFaceBtn.addEventListener('click', captureFaceForTest);
        
        // Upload controls
        if (testUploadBtn) testUploadBtn.addEventListener('click', testUploadRecognition);
        if (detectFacesBtn) detectFacesBtn.addEventListener('click', detectFacesInUpload);
        if (clearPreviewBtn) clearPreviewBtn.addEventListener('click', clearUpload);
        
        // Modal controls
        if (closeTestResult) {
            closeTestResult.addEventListener('click', () => {
                hideModal();
            });
        }
        
        if (testAgainBtn) {
            testAgainBtn.addEventListener('click', () => {
                hideModal();
                if (isCameraOn) {
                    startRealTimeDetection();
                }
            });
        }
        
        // Test Details Modal
        if (closeDetails) {
            closeDetails.addEventListener('click', () => {
                hideDetailsModal();
            });
        }
        
        if (closeDetailsBtn) {
            closeDetailsBtn.addEventListener('click', () => {
                hideDetailsModal();
            });
        }
        
        if (viewInDashboard) {
            viewInDashboard.addEventListener('click', () => {
                window.location.href = '/dashboard';
            });
        }
        
        // Close modals on outside click
        testResultModal.addEventListener('click', (e) => {
            if (e.target === testResultModal) {
                hideModal();
            }
        });
        
        testDetailsModal.addEventListener('click', (e) => {
            if (e.target === testDetailsModal) {
                hideDetailsModal();
            }
        });
    }
    
    function setupUploadArea() {
        if (!uploadArea || !imageUpload) return;
        
        // Click to upload
        uploadArea.addEventListener('click', () => {
            imageUpload.click();
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            if (e.dataTransfer.files.length) {
                handleImageUpload(e.dataTransfer.files[0]);
            }
        });
        
        // File input change
        imageUpload.addEventListener('change', (e) => {
            if (e.target.files.length) {
                handleImageUpload(e.target.files[0]);
            }
        });
    }
    
    async function checkModelStatus() {
        try {
            const response = await fetch('/api/check-model-status');
            const data = await response.json();
            
            if (data.success) {
                modelStatus = data.model_loaded ? 'loaded' : 'error';
                studentCount = data.students_count || 0;
                
                updateStatusDisplay();
                
                // Check database connection
                checkDatabaseConnection();
            }
        } catch (error) {
            console.error('Error checking model status:', error);
            modelStatus = 'error';
            updateStatusDisplay();
            showNotification('Failed to connect to server', 'error');
        }
    }
    
    async function checkDatabaseConnection() {
        try {
            const response = await fetch('/api/get-statistics');
            const data = await response.json();
            
            if (data.success) {
                databaseConnected = true;
                dbStatus.textContent = 'Connected';
                dbStatus.className = 'footer-status status-loaded';
            } else {
                databaseConnected = false;
                dbStatus.textContent = 'Disconnected';
                dbStatus.className = 'footer-status status-error';
            }
        } catch (error) {
            console.error('Error checking database connection:', error);
            databaseConnected = false;
            dbStatus.textContent = 'Disconnected';
            dbStatus.className = 'footer-status status-error';
        }
    }
    
    async function loadStudentsList() {
        try {
            const response = await fetch('/api/get-all-students');
            const data = await response.json();
            
            if (data.success && data.students) {
                studentsList.innerHTML = '';
                
                if (data.students.length === 0) {
                    studentsList.innerHTML = '<div class="no-students">No students found in the model</div>';
                    return;
                }
                
                const studentsGrid = document.createElement('div');
                studentsGrid.className = 'students-grid';
                
                data.students.forEach(student => {
                    const studentCard = document.createElement('div');
                    studentCard.className = 'student-card';
                    studentCard.innerHTML = `
                        <div class="student-avatar">
                            <i class="fas fa-user"></i>
                        </div>
                        <div class="student-info">
                            <h4>${student}</h4>
                            <p>Available for recognition</p>
                        </div>
                    `;
                    studentsGrid.appendChild(studentCard);
                });
                
                studentsList.appendChild(studentsGrid);
            }
        } catch (error) {
            console.error('Error loading students:', error);
            studentsList.innerHTML = '<div class="error-loading">Error loading students list</div>';
        }
    }
    
    function updateStatusDisplay() {
        // Update status indicator
        switch(modelStatus) {
            case 'loaded':
                statusDot.className = 'status-dot success';
                statusText.textContent = 'Model Loaded';
                footerStatus.textContent = 'Loaded';
                footerStatus.className = 'footer-status status-loaded';
                break;
            case 'checking':
                statusDot.className = 'status-dot warning';
                statusText.textContent = 'Checking Model...';
                footerStatus.textContent = 'Checking...';
                footerStatus.className = 'footer-status status-checking';
                break;
            case 'error':
                statusDot.className = 'status-dot error';
                statusText.textContent = 'Model Error';
                footerStatus.textContent = 'Error';
                footerStatus.className = 'footer-status status-error';
                break;
        }
        
        // Update student count
        countText.textContent = `${studentCount} student${studentCount !== 1 ? 's' : ''}`;
    }
    
    function updateCameraStatus() {
        if (cameraStatus) {
            if (isCameraOn) {
                cameraStatus.innerHTML = '<i class="fas fa-video"></i><span>Camera active</span>';
            } else {
                cameraStatus.innerHTML = '<i class="fas fa-video-slash"></i><span>Camera off</span>';
            }
        }
    }
    
    function handleImageUpload(file) {
        if (!file.type.match('image.*')) {
            showNotification('Please select an image file', 'error');
            return;
        }
        
        if (file.size > 16 * 1024 * 1024) {
            showNotification('Image size must be less than 16MB', 'error');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            imagePreview.classList.remove('hidden');
            testUploadBtn.disabled = false;
            detectFacesBtn.disabled = false;
            uploadResults.classList.add('hidden');
        };
        reader.readAsDataURL(file);
    }
    
    async function startCamera() {
        try {
            if (modelStatus !== 'loaded') {
                showNotification('Face recognition model is not loaded', 'error');
                return;
            }
            
            const constraints = {
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user',
                    aspectRatio: 4/3
                },
                audio: false
            };
            
            currentStream = await navigator.mediaDevices.getUserMedia(constraints);
            video.srcObject = currentStream;
            isCameraOn = true;
            
            // Wait for video to be ready
            await new Promise(resolve => {
                video.onloadedmetadata = () => {
                    // Set canvas dimensions to match video
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    
                    // Show face overlay
                    faceOverlay.classList.remove('hidden');
                    resolve();
                };
            });
            
            updateCameraControls();
            updateCameraStatus();
            startRealTimeDetection();
            
            showNotification('Camera started. Real-time face detection active.', 'success');
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            
            if (error.name === 'NotAllowedError') {
                showNotification('Camera permission denied. Please allow camera access.', 'error');
            } else if (error.name === 'NotFoundError') {
                showNotification('No camera found on your device.', 'error');
            } else {
                showNotification('Failed to access camera. Please try again.', 'error');
            }
        }
    }
    
    function stopCamera() {
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
            currentStream = null;
        }
        
        if (video.srcObject) {
            video.srcObject = null;
        }
        
        if (detectionInterval) {
            clearInterval(detectionInterval);
            detectionInterval = null;
        }
        
        // Hide face overlay and processed image
        faceOverlay.classList.add('hidden');
        processedImage.classList.add('hidden');
        video.classList.remove('hidden');
        faceInfo.classList.add('hidden');
        
        isCameraOn = false;
        updateCameraControls();
        updateCameraStatus();
        
        // Hide results
        document.getElementById('recognizedName').textContent = '-';
        document.getElementById('recognitionConfidence').textContent = '-';
        document.getElementById('faceDetected').textContent = '-';
        document.getElementById('recognitionStatus').textContent = 'Idle';
        document.getElementById('recognitionStatus').className = 'value status-pending';
        
        showNotification('Camera stopped', 'info');
    }
    
    function updateCameraControls() {
        if (startCameraBtn) startCameraBtn.disabled = isCameraOn;
        if (stopCameraBtn) stopCameraBtn.disabled = !isCameraOn;
        if (testFaceBtn) testFaceBtn.disabled = !isCameraOn;
        if (captureFaceBtn) captureFaceBtn.disabled = !isCameraOn;
    }
    
    function startRealTimeDetection() {
        if (detectionInterval) clearInterval(detectionInterval);
        
        detectionInterval = setInterval(async () => {
            if (!isCameraOn) {
                clearInterval(detectionInterval);
                return;
            }
            
            await detectFacesWithBoxes();
        }, 1000); // Detect every second
    }
    
    async function detectFacesWithBoxes() {
        if (!isCameraOn) return;
        
        try {
            // Capture frame
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const imageData = canvas.toDataURL('image/jpeg', 0.8);
            
            // Send for face detection with boxes
            const response = await fetch('/api/detect-faces-with-boxes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });
            
            const data = await response.json();
            
            if (data.success && data.processed_image) {
                // Update display with processed image (with boxes)
                processedImage.src = data.processed_image;
                processedImage.classList.remove('hidden');
                video.classList.add('hidden');
                
                // Show recognition info if available
                if (data.recognized_name && data.recognized_name !== 'Unknown') {
                    updateFaceInfo(data.recognized_name, data.confidence);
                } else {
                    faceInfo.classList.add('hidden');
                }
                
                // Update camera results
                updateCameraResults(data);
            }
            
        } catch (error) {
            console.error('Real-time detection error:', error);
        }
    }
    
    async function detectFacesInUpload() {
        if (!previewImage.src) return;
        
        detectFacesBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Detecting...';
        detectFacesBtn.disabled = true;
        
        try {
            const response = await fetch('/api/detect-faces-with-boxes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: previewImage.src })
            });
            
            const data = await response.json();
            
            if (data.success && data.processed_image) {
                // Show processed image
                previewImage.src = data.processed_image;
                
                // Update results
                updateUploadResults(data);
            } else {
                showNotification(data.message || 'Face detection failed', 'error');
            }
            
        } catch (error) {
            console.error('Face detection error:', error);
            showNotification('Error detecting faces', 'error');
        } finally {
            detectFacesBtn.innerHTML = '<i class="fas fa-search"></i><span>Detect Faces</span>';
            detectFacesBtn.disabled = false;
        }
    }
    
    function updateFaceInfo(name, confidence) {
        faceInfo.classList.remove('hidden');
        faceInfoName.textContent = name;
        faceInfoConfidence.textContent = `${confidence}%`;
        
        // Update confidence color
        if (confidence > 75) {
            faceInfoConfidence.className = 'face-info-confidence confidence-high';
        } else if (confidence > 50) {
            faceInfoConfidence.className = 'face-info-confidence confidence-medium';
        } else {
            faceInfoConfidence.className = 'face-info-confidence confidence-low';
        }
    }
    
    function updateCameraResults(data) {
        document.getElementById('recognizedName').textContent = data.recognized_name || 'Unknown';
        document.getElementById('recognitionConfidence').textContent = data.confidence + '%';
        document.getElementById('faceDetected').textContent = data.has_face ? 'Yes' : 'No';
        
        const statusElement = document.getElementById('recognitionStatus');
        if (data.recognized_name && data.recognized_name !== 'Unknown') {
            statusElement.textContent = 'Recognized';
            statusElement.className = 'value status-success';
        } else if (data.has_face) {
            statusElement.textContent = 'Face Detected (Unknown)';
            statusElement.className = 'value status-warning';
        } else {
            statusElement.textContent = 'No Face';
            statusElement.className = 'value status-error';
        }
    }
    
    function updateUploadResults(data) {
        uploadResults.classList.remove('hidden');
        
        document.getElementById('uploadRecognizedName').textContent = data.recognized_name || 'Unknown';
        document.getElementById('uploadConfidence').textContent = data.confidence + '%';
        
        const resultElement = document.getElementById('uploadResult');
        if (data.recognized_name && data.recognized_name !== 'Unknown') {
            resultElement.textContent = 'Recognized';
            resultElement.className = 'value status-success';
        } else if (data.has_face) {
            resultElement.textContent = 'Face Detected (Unknown)';
            resultElement.className = 'value status-warning';
        } else {
            resultElement.textContent = 'No Face';
            resultElement.className = 'value status-error';
        }
    }
    
    async function testFaceRecognition() {
        if (!isCameraOn) {
            showNotification('Please start camera first', 'warning');
            return;
        }
        
        // Show loading
        testFaceBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
        testFaceBtn.disabled = true;
        
        try {
            // Capture frame
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const imageData = canvas.toDataURL('image/jpeg', 0.9);
            
            // Send for testing (without database logging)
            const response = await fetch('/api/test-face-recognition?type=Live Camera Test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showTestResult(
                    'success',
                    'Recognition Test Complete',
                    `Recognized as: ${data.recognized_name}<br>Confidence: ${data.confidence}%<br><br>Click "Capture Face" to save this test to database.`
                );
            } else {
                showTestResult('error', 'Recognition Failed', data.message);
            }
            
        } catch (error) {
            console.error('Test error:', error);
            showTestResult('error', 'Network Error', 'Please check your connection');
        } finally {
            // Reset button
            testFaceBtn.innerHTML = '<i class="fas fa-user-check"></i><span>Test Recognition</span>';
            testFaceBtn.disabled = false;
        }
    }
    
    async function captureFaceForTest() {
        if (!isCameraOn) return;
        
        captureFaceBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Capturing...';
        captureFaceBtn.disabled = true;
        
        try {
            // Capture frame
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const imageData = canvas.toDataURL('image/jpeg', 0.9);
            
            // Send for face capture test (this will log to database)
            const response = await fetch('/api/capture-face', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Show detailed test results
                showTestDetails({
                    testType: 'Live Camera Test',
                    timestamp: new Date().toLocaleString(),
                    student: data.recognized_name || 'Unknown',
                    confidence: data.confidence,
                    dbStatus: databaseConnected ? 'Logged to database' : 'Database error'
                });
                
                showNotification(
                    `Face ${data.face_detected ? 'detected' : 'not detected'}. ${databaseConnected ? 'Saved to database.' : 'Database not connected.'}`,
                    data.face_detected ? 'success' : 'warning'
                );
            }
            
        } catch (error) {
            console.error('Capture error:', error);
            showNotification('Error capturing face', 'error');
        } finally {
            captureFaceBtn.innerHTML = '<i class="fas fa-camera"></i><span>Capture Face</span>';
            captureFaceBtn.disabled = false;
        }
    }
    
    async function testUploadRecognition() {
        if (!previewImage.src) return;
        
        // Show loading
        testUploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
        testUploadBtn.disabled = true;
        
        try {
            // Create form data
            const formData = new FormData();
            const blob = await fetch(previewImage.src).then(r => r.blob());
            formData.append('image', blob, 'test.jpg');
            
            // Send for testing (this will automatically log to database)
            const response = await fetch('/api/test-face-recognition?type=Upload Image Test', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Show detailed test results
                showTestDetails({
                    testType: 'Upload Image Test',
                    timestamp: new Date().toLocaleString(),
                    student: data.recognized_name || 'Unknown',
                    confidence: data.confidence,
                    dbStatus: databaseConnected ? 'Logged to database' : 'Database error'
                });
                
                showTestResult(
                    'success',
                    'Upload Test Complete',
                    `Recognized as: ${data.recognized_name}<br>Confidence: ${data.confidence}%<br><br>Test has been saved to database.`
                );
            } else {
                showTestResult('error', 'Recognition Failed', data.message);
            }
            
        } catch (error) {
            console.error('Upload test error:', error);
            showTestResult('error', 'Network Error', 'Please check your connection');
        } finally {
            // Reset button
            testUploadBtn.innerHTML = '<i class="fas fa-user-check"></i><span>Test Recognition</span>';
            testUploadBtn.disabled = false;
        }
    }
    
    function clearUpload() {
        imageUpload.value = '';
        previewImage.src = '';
        imagePreview.classList.add('hidden');
        uploadResults.classList.add('hidden');
        testUploadBtn.disabled = true;
        detectFacesBtn.disabled = true;
    }
    
    function showTestResult(type, title, message) {
        // Update modal content
        if (type === 'success') {
            testResultIcon.innerHTML = '<div class="icon-success"><i class="fas fa-check"></i></div>';
            testResultTitle.textContent = title;
            testResultTitle.className = 'modal-title success';
            testResultMessage.innerHTML = message;
        } else {
            testResultIcon.innerHTML = '<div class="icon-error"><i class="fas fa-times"></i></div>';
            testResultTitle.textContent = title;
            testResultTitle.className = 'modal-title error';
            testResultMessage.textContent = message;
        }
        
        // Show modal
        testResultModal.classList.remove('hidden');
    }
    
    function showTestDetails(details) {
        // Update details modal content
        document.getElementById('detailTestType').textContent = details.testType;
        document.getElementById('detailTimestamp').textContent = details.timestamp;
        document.getElementById('detailStudent').textContent = details.student;
        document.getElementById('detailConfidence').textContent = `${details.confidence}%`;
        document.getElementById('detailDbStatus').textContent = details.dbStatus;
        
        // Color code the database status
        const dbStatusElement = document.getElementById('detailDbStatus');
        if (details.dbStatus.includes('error')) {
            dbStatusElement.style.color = '#ef4444';
        } else {
            dbStatusElement.style.color = '#10b981';
        }
        
        // Show modal
        testDetailsModal.classList.remove('hidden');
    }
    
    function hideModal() {
        testResultModal.classList.add('hidden');
    }
    
    function hideDetailsModal() {
        testDetailsModal.classList.add('hidden');
    }
    
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        const container = document.getElementById('notificationContainer');
        container.appendChild(notification);
        
        // Add close button event
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    // Clean up
    window.addEventListener('beforeunload', () => {
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
        }
        if (detectionInterval) {
            clearInterval(detectionInterval);
        }
    });
});