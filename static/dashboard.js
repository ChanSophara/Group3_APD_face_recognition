document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const confidenceTrendChartCanvas = document.getElementById('confidenceTrendChart');
    const historyTableBody = document.getElementById('historyTableBody');
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');
    const pageInfo = document.getElementById('pageInfo');
    
    // Statistics elements
    const totalTestsEl = document.getElementById('totalTests');
    const uniqueStudentsEl = document.getElementById('uniqueStudents');
    const avgConfidenceEl = document.getElementById('avgConfidence');
    
    // Chart instance
    let confidenceTrendChart = null;
    
    // State
    let currentPage = 1;
    let totalPages = 1;
    const itemsPerPage = 10;
    
    // Initialize
    initializeDashboard();
    
    function initializeDashboard() {
        setupEventListeners();
        loadStatistics();
        loadHistory();
    }
    
    function setupEventListeners() {
        // Pagination
        prevPageBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                loadHistory();
            }
        });
        
        nextPageBtn.addEventListener('click', () => {
            if (currentPage < totalPages) {
                currentPage++;
                loadHistory();
            }
        });
    }
    
    async function loadStatistics() {
        try {
            const response = await fetch('/api/get-statistics');
            const data = await response.json();
            
            if (data.success) {
                const stats = data.statistics;
                
                totalTestsEl.textContent = stats.total_tests.toLocaleString();
                uniqueStudentsEl.textContent = stats.unique_students.toLocaleString();
                avgConfidenceEl.textContent = `${stats.avg_confidence}%`;
                
                // Load confidence trend data
                loadConfidenceTrend();
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
            showNotification('Error loading statistics', 'error');
        }
    }
    
    async function loadConfidenceTrend() {
        try {
            const response = await fetch('/api/get-recognition-history?limit=50');
            const data = await response.json();
            
            if (data.success && data.history && data.history.length > 0) {
                createConfidenceTrendChart(data.history);
            } else {
                // Show empty state if no data
                confidenceTrendChartCanvas.parentElement.innerHTML = `
                    <div style="text-align: center; padding: 60px; color: #6b7280;">
                        <i class="fas fa-chart-line" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
                        <p>No recognition data available yet</p>
                        <p style="font-size: 14px; margin-top: 8px;">Start testing to see confidence trends</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading confidence trend:', error);
            showNotification('Error loading confidence trend', 'error');
        }
    }
    
    async function loadHistory() {
        try {
            const offset = (currentPage - 1) * itemsPerPage;
            const response = await fetch(`/api/get-recognition-history?limit=${itemsPerPage}&offset=${offset}`);
            const data = await response.json();
            
            if (data.success) {
                totalPages = Math.ceil(data.count / itemsPerPage);
                renderHistoryTable(data.history);
                updatePagination();
            }
        } catch (error) {
            console.error('Error loading history:', error);
            showNotification('Error loading recognition history', 'error');
            historyTableBody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; padding: 40px; color: #ef4444;">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Error loading history</span>
                    </td>
                </tr>
            `;
        }
    }
    
    function renderHistoryTable(data = []) {
        if (data.length === 0) {
            historyTableBody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; padding: 40px; color: #6b7280;">
                        <i class="fas fa-inbox"></i>
                        <span>No recognition records found</span>
                    </td>
                </tr>
            `;
            return;
        }
        
        const rows = data.map(item => {
            const timestamp = new Date(item.timestamp).toLocaleString();
            const confidence = item.confidence || 0;
            let confidenceClass;
            
            if (confidence >= 70) {
                confidenceClass = 'confidence-high';
            } else if (confidence >= 40) {
                confidenceClass = 'confidence-medium';
            } else {
                confidenceClass = 'confidence-low';
            }
            
            return `
                <tr>
                    <td>${timestamp}</td>
                    <td>
                        <span style="display: inline-block; padding: 4px 8px; background: #f3f4f6; border-radius: 4px; font-size: 12px;">
                            ${item.test_type}
                        </span>
                    </td>
                    <td>
                        <strong>${item.student_name || 'Unknown'}</strong>
                    </td>
                    <td>
                        <span class="confidence-badge ${confidenceClass}">
                            ${confidence}%
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
        
        historyTableBody.innerHTML = rows;
    }
    
    function updatePagination() {
        prevPageBtn.disabled = currentPage === 1;
        nextPageBtn.disabled = currentPage === totalPages;
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    }
    
    function createConfidenceTrendChart(historyData) {
        // Sort by timestamp
        const sortedData = [...historyData].sort((a, b) => 
            new Date(a.timestamp) - new Date(b.timestamp)
        );
        
        // Prepare data for chart
        const timestamps = sortedData.map(item => 
            new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        );
        
        const confidences = sortedData.map(item => item.confidence || 0);
        const labels = sortedData.map(item => item.student_name || 'Unknown');
        
        // Destroy existing chart
        if (confidenceTrendChart) {
            confidenceTrendChart.destroy();
        }
        
        confidenceTrendChart = new Chart(confidenceTrendChartCanvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Confidence Score',
                    data: confidences,
                    borderColor: '#4361ee',
                    backgroundColor: 'rgba(67, 97, 238, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: function(context) {
                        const confidence = confidences[context.dataIndex];
                        if (confidence >= 70) return '#10b981';
                        if (confidence >= 40) return '#f59e0b';
                        return '#ef4444';
                    },
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const index = context.dataIndex;
                                const student = labels[index];
                                const confidence = confidences[index];
                                return `${student}: ${confidence}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            font: {
                                family: 'Inter',
                                size: 11
                            },
                            maxRotation: 45
                        },
                        title: {
                            display: true,
                            text: 'Time',
                            font: {
                                family: 'Inter',
                                weight: '500',
                                size: 12
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            font: {
                                family: 'Inter',
                                size: 11
                            },
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Confidence Score',
                            font: {
                                family: 'Inter',
                                weight: '500',
                                size: 12
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
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
});