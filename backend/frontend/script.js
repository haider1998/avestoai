// AvestoAI Frontend JavaScript
const API_BASE_URL = 'http://localhost:8080';

// Global state
let currentUser = {
    mobile_number: '',
    session_id: '',
    is_authenticated: false,
    scenario: 'balanced'
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    checkBackendStatus();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Enter key handlers
    document.getElementById('mobileNumber').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') initiateAuth();
    });
    
    document.getElementById('otpInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') verifyOTP();
    });
}

// Check backend status
async function checkBackendStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (response.ok && data.status === 'healthy') {
            updateStatusIndicator('connected', 'Backend Connected');
        } else {
            updateStatusIndicator('disconnected', 'Backend Issues');
        }
    } catch (error) {
        updateStatusIndicator('disconnected', 'Backend Offline');
        console.error('Backend status check failed:', error);
    }
}

// Update status indicator
function updateStatusIndicator(status, text) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    indicator.className = `status-indicator ${status}`;
    statusText.textContent = text;
}

// Show loading overlay
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} fade-in`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        ${message}
    `;
    
    // Insert at the top of main content
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(alertDiv, mainContent.firstChild);
    
    // Remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Initiate Fi MCP authentication
async function initiateAuth() {
    const mobileNumber = document.getElementById('mobileNumber').value.trim();
    const scenario = document.getElementById('scenario').value;
    
    if (!mobileNumber || mobileNumber.length !== 10) {
        showAlert('Please enter a valid 10-digit mobile number', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/fi-auth/initiate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mobile_number: mobileNumber,
                scenario: scenario
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentUser.mobile_number = mobileNumber;
            currentUser.session_id = data.session_id;
            currentUser.scenario = scenario;
            
            if (data.requires_authentication && data.login_url) {
                showAlert(`Authentication initiated. Please complete login at: ${data.login_url}`, 'info');
                // In a real app, you might open this URL in a new window
                window.open(data.login_url, '_blank');
            }
            
            // Show OTP section
            document.getElementById('otpSection').style.display = 'block';
            showAlert('Please enter the OTP sent to your mobile number', 'success');
        } else {
            showAlert(`Authentication failed: ${data.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Auth initiation failed:', error);
        showAlert('Failed to initiate authentication. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// Verify OTP
async function verifyOTP() {
    const otp = document.getElementById('otpInput').value.trim();
    
    if (!otp || otp.length !== 6) {
        showAlert('Please enter a valid 6-digit OTP', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/fi-auth/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mobile_number: currentUser.mobile_number,
                session_id: currentUser.session_id,
                otp: otp
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            currentUser.is_authenticated = true;
            
            // Update user info
            document.getElementById('netWorth').textContent = `₹${formatNumber(data.net_worth)}`;
            document.getElementById('accountsCount').textContent = data.accounts_count;
            
            // Hide auth section and show dashboard
            document.getElementById('authSection').style.display = 'none';
            document.getElementById('dashboardSection').style.display = 'block';
            
            showAlert('Authentication successful! Welcome to AvestoAI.', 'success');
            
            // Load initial dashboard data
            loadDashboardData();
        } else {
            showAlert(`OTP verification failed: ${data.message || 'Invalid OTP'}`, 'error');
        }
    } catch (error) {
        console.error('OTP verification failed:', error);
        showAlert('Failed to verify OTP. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// Load dashboard data
async function loadDashboardData() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/financial-dashboard/${currentUser.mobile_number}`);
        const data = await response.json();
        
        if (response.ok) {
            // Update health score
            document.getElementById('healthScore').textContent = `${Math.round(data.health_score?.score || 0)}%`;
            
            // You can add more dashboard updates here
        }
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

// Analyze opportunities
async function analyzeOpportunities() {
    if (!currentUser.is_authenticated) {
        showAlert('Please authenticate first', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/analyze-opportunities`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mobile_number: currentUser.mobile_number,
                analysis_type: 'comprehensive'
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayOpportunities(data);
            showAlert(`Found ${data.opportunities?.length || 0} opportunities!`, 'success');
        } else {
            showAlert(`Analysis failed: ${data.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Opportunity analysis failed:', error);
        showAlert('Failed to analyze opportunities. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// Display opportunities
function displayOpportunities(data) {
    const resultsSection = document.getElementById('resultsSection');
    
    let html = `
        <h3><i class="fas fa-lightbulb"></i> Financial Opportunities</h3>
        <p>Analysis completed in ${data.processing_time?.toFixed(1)}ms</p>
    `;
    
    if (data.opportunities && data.opportunities.length > 0) {
        data.opportunities.forEach(opportunity => {
            html += `
                <div class="opportunity-card fade-in">
                    <h4>${opportunity.title || 'Investment Opportunity'}</h4>
                    <p>${opportunity.description || 'No description available'}</p>
                    <div style="margin-top: 10px;">
                        <strong>Potential Impact:</strong> ${opportunity.impact || 'Positive'}
                    </div>
                </div>
            `;
        });
    } else {
        html += '<p>No specific opportunities found at this time.</p>';
    }
    
    resultsSection.innerHTML = html;
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Open decision analyzer
function openDecisionAnalyzer() {
    if (!currentUser.is_authenticated) {
        showAlert('Please authenticate first', 'error');
        return;
    }
    
    document.getElementById('decisionModal').style.display = 'block';
}

// Close decision analyzer
function closeDecisionAnalyzer() {
    document.getElementById('decisionModal').style.display = 'none';
    document.getElementById('decisionResults').innerHTML = '';
}

// Analyze decision
async function analyzeDecision() {
    const amount = document.getElementById('decisionAmount').value;
    const category = document.getElementById('decisionCategory').value;
    const description = document.getElementById('decisionDescription').value;
    
    if (!amount || !description) {
        showAlert('Please fill in all required fields', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/predict-decision`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mobile_number: currentUser.mobile_number,
                amount: parseFloat(amount),
                category: category,
                description: description,
                user_context: {}
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayDecisionResults(data);
        } else {
            showAlert(`Decision analysis failed: ${data.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Decision analysis failed:', error);
        showAlert('Failed to analyze decision. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// Display decision results
function displayDecisionResults(data) {
    const resultsDiv = document.getElementById('decisionResults');
    const score = data.score || 0;
    const scoreClass = score >= 70 ? 'score-good' : score >= 40 ? 'score-medium' : 'score-poor';
    
    let html = `
        <div class="decision-score">
            <div class="score-circle ${scoreClass}">
                ${Math.round(score)}%
            </div>
            <div>
                <h4>Decision Score</h4>
                <p>${data.recommendation || 'Analysis completed'}</p>
            </div>
        </div>
    `;
    
    if (data.reasoning) {
        html += `
            <div style="margin-top: 20px;">
                <h5>Analysis Reasoning:</h5>
                <p>${data.reasoning}</p>
            </div>
        `;
    }
    
    if (data.risks && data.risks.length > 0) {
        html += `
            <div style="margin-top: 20px;">
                <h5>Identified Risks:</h5>
                <ul>
                    ${data.risks.map(risk => `<li>${risk}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    resultsDiv.innerHTML = html;
}

// Open chat
function openChat() {
    if (!currentUser.is_authenticated) {
        showAlert('Please authenticate first', 'error');
        return;
    }
    
    document.getElementById('chatModal').style.display = 'block';
}

// Close chat
function closeChat() {
    document.getElementById('chatModal').style.display = 'none';
}

// Handle chat key press
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

// Send chat message
async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addChatMessage(message, 'user');
    input.value = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/agentic-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mobile_number: currentUser.mobile_number,
                message: message
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            addChatMessage(data.response || 'I apologize, but I couldn\'t process your request.', 'ai');
        } else {
            addChatMessage('Sorry, I encountered an error. Please try again.', 'ai');
        }
    } catch (error) {
        console.error('Chat message failed:', error);
        addChatMessage('Sorry, I\'m having trouble connecting. Please try again.', 'ai');
    }
}

// Add message to chat
function addChatMessage(message, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message fade-in`;
    
    const icon = sender === 'user' ? 'fa-user' : 'fa-robot';
    
    messageDiv.innerHTML = `
        <i class="fas ${icon}"></i>
        <div class="message-content">${message}</div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// View dashboard
async function viewDashboard() {
    if (!currentUser.is_authenticated) {
        showAlert('Please authenticate first', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/financial-dashboard/${currentUser.mobile_number}`);
        const data = await response.json();
        
        if (response.ok) {
            displayDashboard(data);
            showAlert('Dashboard loaded successfully!', 'success');
        } else {
            showAlert(`Failed to load dashboard: ${data.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Dashboard loading failed:', error);
        showAlert('Failed to load dashboard. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// Display dashboard
function displayDashboard(data) {
    const resultsSection = document.getElementById('resultsSection');
    
    let html = `
        <h3><i class="fas fa-chart-pie"></i> Financial Dashboard</h3>
        <div class="user-stats" style="margin-top: 20px;">
    `;
    
    if (data.financial_summary) {
        const summary = data.financial_summary;
        html += `
            <div class="stat-card">
                <i class="fas fa-coins"></i>
                <div>
                    <span class="stat-value">₹${formatNumber(summary.total_assets || 0)}</span>
                    <span class="stat-label">Total Assets</span>
                </div>
            </div>
            <div class="stat-card">
                <i class="fas fa-credit-card"></i>
                <div>
                    <span class="stat-value">₹${formatNumber(summary.total_liabilities || 0)}</span>
                    <span class="stat-label">Total Liabilities</span>
                </div>
            </div>
            <div class="stat-card">
                <i class="fas fa-chart-line"></i>
                <div>
                    <span class="stat-value">₹${formatNumber(summary.monthly_income || 0)}</span>
                    <span class="stat-label">Monthly Income</span>
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    
    if (data.insights && data.insights.length > 0) {
        html += `
            <h4 style="margin-top: 30px;"><i class="fas fa-lightbulb"></i> Key Insights</h4>
        `;
        
        data.insights.forEach(insight => {
            html += `
                <div class="opportunity-card fade-in">
                    <h5>${insight.title || 'Financial Insight'}</h5>
                    <p>${insight.description || insight}</p>
                </div>
            `;
        });
    }
    
    resultsSection.innerHTML = html;
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Utility function to format numbers
function formatNumber(num) {
    if (num >= 10000000) {
        return (num / 10000000).toFixed(1) + 'Cr';
    } else if (num >= 100000) {
        return (num / 100000).toFixed(1) + 'L';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Close modals when clicking outside
window.onclick = function(event) {
    const chatModal = document.getElementById('chatModal');
    const decisionModal = document.getElementById('decisionModal');
    
    if (event.target === chatModal) {
        closeChat();
    }
    if (event.target === decisionModal) {
        closeDecisionAnalyzer();
    }
}
