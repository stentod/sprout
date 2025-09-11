// Analytics JavaScript - Clean Implementation
console.log('📊 Analytics page loading...');

// Configuration
const API_BASE_URL = getApiBaseUrl();
let spendingChart = null;

// Get API base URL
function getApiBaseUrl() {
  const isDevelopment = window.location.hostname === 'localhost' && window.location.port !== '';
  const isLivereload = window.location.port === '8080' || window.location.port === '3000';
  
  if (isDevelopment && isLivereload) {
    const apiPort = window.ENV_API_PORT || '5001';
    return `http://localhost:${apiPort}`;
  }
  
  return '';
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
  console.log('📊 Analytics page initialized');
  
  // Check authentication
  checkAuth();
  
  // Set up event listeners
  setupEventListeners();
  
  // Load initial data
  loadAnalyticsData();
  
  // Set up periodic refresh every 30 seconds to catch any changes
  setInterval(function() {
    console.log('⏰ Periodic refresh of analytics data');
    loadAnalyticsData();
  }, 30000);
});

// Check authentication
async function checkAuth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/summary`, {
      credentials: 'include'
    });
    
    if (!response.ok) {
      console.log('🔒 Not authenticated, redirecting...');
      window.location.href = '/auth.html';
      return;
    }
    
    console.log('✅ User authenticated');
  } catch (error) {
    console.error('❌ Auth check failed:', error);
    window.location.href = '/auth.html';
  }
}

// Set up event listeners
function setupEventListeners() {
  // Time range selector
  const timeRangeSelect = document.getElementById('timeRange');
  if (timeRangeSelect) {
    timeRangeSelect.addEventListener('change', function() {
      console.log('📅 Time range changed to:', this.value);
      loadAnalyticsData();
    });
  }
  
  // Refresh button
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', function() {
      console.log('🔄 Refresh button clicked');
      loadAnalyticsData();
    });
  }
  
  // Listen for URL changes (when day offset changes)
  window.addEventListener('popstate', function() {
    console.log('📅 URL changed, reloading analytics data');
    loadAnalyticsData();
  });
  
  // Listen for page visibility changes (when user comes back from main page)
  document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
      console.log('👁️ Page became visible, refreshing analytics data');
      loadAnalyticsData();
    }
  });
  
}

// Load analytics data
async function loadAnalyticsData() {
  const loadingOverlay = document.getElementById('loadingOverlay');
  const timeRange = document.getElementById('timeRange').value;
  
  try {
    // Show loading
    showLoading(true);
    
    console.log(`📊 Loading data for ${timeRange} days`);
    
    // Get current day offset from URL parameters (for date simulation)
    const urlParams = new URLSearchParams(window.location.search);
    const dayOffset = urlParams.get('dayOffset') || '0';
    
    
    // Fetch data with day offset parameter
    const response = await fetch(`${API_BASE_URL}/api/analytics/daily-spending?days=${timeRange}&dayOffset=${dayOffset}`, {
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('📊 Data received:', result);
    
    if (result.success) {
      updateSummaryCards(result.summary);
      createChart(result.data, result.summary);
    } else {
      throw new Error(result.error || 'Failed to load data');
    }
    
  } catch (error) {
    console.error('❌ Error loading data:', error);
    showError('Failed to load analytics data. Please try again.');
  } finally {
    showLoading(false);
  }
}

// Update summary cards
function updateSummaryCards(summary) {
  console.log('📊 Updating summary cards:', summary);
  
  // Total spent
  const totalSpentEl = document.getElementById('totalSpent');
  if (totalSpentEl) {
    totalSpentEl.textContent = `$${summary.total_spent.toFixed(2)}`;
  }
  
  // Daily average
  const dailyAverageEl = document.getElementById('dailyAverage');
  if (dailyAverageEl) {
    dailyAverageEl.textContent = `$${summary.average_daily.toFixed(2)}`;
  }
  
  // Budget limit
  const budgetLimitEl = document.getElementById('budgetLimit');
  if (budgetLimitEl) {
    budgetLimitEl.textContent = `$${summary.daily_budget_limit.toFixed(2)}`;
  }
  
  // Days over budget
  const daysOverBudgetEl = document.getElementById('daysOverBudget');
  if (daysOverBudgetEl) {
    daysOverBudgetEl.textContent = summary.days_over_budget;
    
    // Color coding
    if (summary.days_over_budget > 0) {
      daysOverBudgetEl.style.color = '#FF6B6B';
    } else {
      daysOverBudgetEl.style.color = '#4CAF50';
    }
  }
}

// Create spending chart
function createChart(data, summary) {
  console.log('📈 Creating chart with data:', data);
  
  const ctx = document.getElementById('spendingChart');
  if (!ctx) {
    console.error('❌ Chart canvas not found');
    return;
  }
  
  // Destroy existing chart
  if (spendingChart) {
    console.log('🗑️ Destroying existing chart');
    spendingChart.destroy();
    spendingChart = null;
  }
  
  // Prepare chart data
  const labels = data.map(item => {
    // Parse the date string correctly to avoid timezone issues
    // Split the date string and create a local date object
    const [year, month, day] = item.date.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    const formatted = date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    });
    return formatted;
  });
  
  const spendingData = data.map(item => item.amount);
  const budgetLimit = summary.daily_budget_limit;
  const budgetLineData = new Array(data.length).fill(budgetLimit);
  
  // Chart configuration
  const config = {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Daily Spending',
          data: spendingData,
          borderColor: '#4CAF50',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#4CAF50',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8
        },
        {
          label: 'Budget Limit',
          data: budgetLineData,
          borderColor: '#FF6B6B',
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [5, 5],
          fill: false,
          pointRadius: 0,
          pointHoverRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: `Daily Spending Trends (${summary.total_days} days)`,
          font: {
            size: 18,
            weight: 'bold'
          },
          color: '#ffffff'
        },
        legend: {
          display: true,
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: 20,
            font: {
              size: 14
            },
            color: '#ffffff'
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: '#4CAF50',
          borderWidth: 1,
          callbacks: {
            title: function(context) {
              const dataIndex = context[0].dataIndex;
              const date = new Date(data[dataIndex].date);
              return date.toLocaleDateString('en-US', { 
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              });
            },
            label: function(context) {
              const label = context.dataset.label || '';
              const value = context.parsed.y;
              const dataIndex = context.dataIndex;
              const transactionCount = data[dataIndex].count;
              
              if (label === 'Daily Spending') {
                return `${label}: $${value.toFixed(2)} (${transactionCount} transaction${transactionCount !== 1 ? 's' : ''})`;
              } else {
                return `${label}: $${value.toFixed(2)}`;
              }
            }
          }
        }
      },
      scales: {
        x: {
          display: true,
          title: {
            display: true,
            text: 'Date',
            font: {
              size: 14,
              weight: 'bold'
            },
            color: '#ffffff'
          },
          grid: {
            display: true,
            color: 'rgba(255, 255, 255, 0.1)'
          },
          ticks: {
            color: '#ffffff'
          }
        },
        y: {
          display: true,
          title: {
            display: true,
            text: 'Amount ($)',
            font: {
              size: 14,
              weight: 'bold'
            },
            color: '#ffffff'
          },
          grid: {
            display: true,
            color: 'rgba(255, 255, 255, 0.1)'
          },
          beginAtZero: true,
          ticks: {
            color: '#ffffff',
            callback: function(value) {
              return '$' + value.toFixed(0);
            }
          }
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  };
  
  // Create chart
  spendingChart = new Chart(ctx, config);
  console.log('✅ Chart created successfully');
}

// Update current date display
function updateCurrentDateDisplay(dayOffset) {
  const currentDateEl = document.getElementById('currentDate');
  if (currentDateEl) {
    const today = new Date();
    const targetDate = new Date(today);
    targetDate.setDate(today.getDate() + dayOffset);
    
    const dateStr = targetDate.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
    
    currentDateEl.textContent = dateStr;
    
    if (dayOffset !== 0) {
      currentDateEl.style.color = '#FFBB33';
      currentDateEl.title = `Simulated date (${dayOffset > 0 ? '+' : ''}${dayOffset} days from today)`;
    } else {
      currentDateEl.style.color = '#4CAF50';
      currentDateEl.title = 'Current date';
    }
  }
}

// Show/hide loading overlay
function showLoading(show) {
  const loadingOverlay = document.getElementById('loadingOverlay');
  if (loadingOverlay) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
  }
}

// Show error message
function showError(message) {
  console.error('❌ Error:', message);
  
  // Create error notification
  const errorDiv = document.createElement('div');
  errorDiv.className = 'error-notification';
  errorDiv.innerHTML = `
    <div class="error-content">
      <span class="error-icon">⚠️</span>
      <span class="error-message">${message}</span>
      <button class="error-close" onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
  `;
  
  document.body.appendChild(errorDiv);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (errorDiv.parentElement) {
      errorDiv.remove();
    }
  }, 5000);
}

// Handle window resize
window.addEventListener('resize', function() {
  if (spendingChart) {
    spendingChart.resize();
  }
});


console.log('📊 Analytics JavaScript loaded successfully');