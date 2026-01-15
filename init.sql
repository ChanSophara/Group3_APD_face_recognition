-- init.sql
-- This will run automatically when PostgreSQL container starts

-- Create recognition_history table if not exists
CREATE TABLE IF NOT EXISTS recognition_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    test_type VARCHAR(50) NOT NULL CHECK (test_type IN ('Live Camera Test', 'Upload Image Test')),
    student_name VARCHAR(255),
    confidence DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indices
CREATE INDEX IF NOT EXISTS idx_recognition_history_timestamp ON recognition_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_recognition_history_test_type ON recognition_history(test_type);
CREATE INDEX IF NOT EXISTS idx_recognition_history_student ON recognition_history(student_name);

-- Insert sample data (optional)
-- INSERT INTO recognition_history (test_type, student_name, confidence) 
-- VALUES ('Upload Image Test', 'John Doe', 85.5);