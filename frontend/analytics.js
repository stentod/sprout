// Analytics JavaScript - Clean Implementation
console.log('📊 Analytics page loading...');

// Configuration
const API_BASE_URL = getApiBaseUrl();
let spendingChart = null;
let categoryChart = null;

// Get API base URL
function getApiBaseUrl() {
  const isDevelopment = window.location.hostname === 'localhost' && window.location.port !== '';
  const isLivereload = window.location.port === '8080' || window.location.port === '3000';
  
  if (isDevelopment && isLivereload) {
    const apiPort = window.ENV_API_PORT || '5001';
    return `http://localhost:${apiPort}`;
  }
  
  // For production, use relative URLs (same domain)
  return '';
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
  console.log('📊 Analytics page initialized');
  console.log('🌐 Current URL:', window.location.href);
  console.log('🔗 API Base URL:', API_BASE_URL);
  console.log('🌍 Environment:', window.location.hostname === 'localhost' ? 'Development' : 'Production');
  console.log('📊 Chart.js Available:', typeof Chart !== 'undefined' ? 'Yes' : 'No');
  
  // Check if Chart.js is loaded
  if (typeof Chart === 'undefined') {
    console.error('❌ Chart.js is not loaded! This will cause charts to fail.');
    showError('Chart.js library failed to load. Please refresh the page.');
    return;
  }
  
  // Check authentication
  checkAuth();
  
  // Set up event listeners
  setupEventListeners();
  
  // Test analytics API first
  testAnalyticsAPI();
  
  // Load initial data
  loadAnalyticsData();
});

// Test analytics API
async function testAnalyticsAPI() {
  try {
    console.log('🧪 Testing analytics API...');
    const response = await fetch(`${API_BASE_URL}/api/analytics/test`, {
      credentials: 'include'
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('✅ Analytics API test successful:', result);
    } else {
      const errorText = await response.text();
      console.error('❌ Analytics API test failed:', response.status, errorText);
    }
  } catch (error) {
    console.error('❌ Analytics API test error:', error);
  }
}

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

// Load analytics data with sequential loading to prevent server overload
async function loadAnalyticsData() {
  const loadingOverlay = document.getElementById('loadingOverlay');
  const timeRange = document.getElementById('timeRange').value;
  
  // Add a safety timeout to force hide loading after 15 seconds
  const safetyTimeout = setTimeout(() => {
    console.warn('⚠️ Safety timeout: forcing loading overlay to hide');
    showLoading(false);
  }, 15000);
  
  try {
    // Show loading
    showLoading(true);
    
    console.log(`📊 Loading data for ${timeRange} days (sequential loading to prevent server overload)`);
    
    // Get current day offset from URL parameters (for date simulation)
    const urlParams = new URLSearchParams(window.location.search);
    const dayOffset = urlParams.get('dayOffset') || '0';
    
    // Keep full data range but load sequentially to prevent server overload
    const isProduction = window.location.hostname !== 'localhost';
    
    if (isProduction) {
      console.log('🌐 Production mode: using optimized sequential loading for 30 days');
    }
    
    // Load data sequentially with delays to prevent server overload
    console.log('🔄 Loading daily spending data...');
    const response = await fetch(`${API_BASE_URL}/api/analytics/daily-spending?days=${timeRange}&dayOffset=${dayOffset}`, {
      credentials: 'include',
      headers: {
        'Cache-Control': 'no-cache'
      }
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ API Error Response:', errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('📊 Data received:', result);
    
    if (result.success) {
      updateSummaryCards(result.summary);
      createChart(result.data, result.summary);
      
      // Load additional components sequentially with delays to prevent server overload
      console.log('📊 Loading category breakdown...');
      try {
        // Add delay to prevent server overload (reduced for better UX)
        await new Promise(resolve => setTimeout(resolve, 500));
        await loadCategoryData();
        console.log('✅ Category breakdown loaded');
      } catch (error) {
        console.warn('⚠️ Category breakdown failed:', error);
      }
      
      console.log('📊 Loading heatmap...');
      try {
        // Add delay to prevent server overload (reduced for better UX)
        await new Promise(resolve => setTimeout(resolve, 500));
        await loadHeatmapData();
        console.log('✅ Heatmap loaded');
      } catch (error) {
        console.warn('⚠️ Heatmap failed:', error);
      }
      
      console.log('✅ All analytics components loaded');
    } else {
      throw new Error(result.error || 'Failed to load data');
    }
    
  } catch (error) {
    console.error('❌ Error loading data:', error);
    showError('Failed to load analytics data. Please try again.');
    
    // Try to load basic data as fallback
    try {
      console.log('🔄 Attempting fallback data loading...');
      await loadBasicAnalytics();
    } catch (fallbackError) {
      console.error('❌ Fallback loading also failed:', fallbackError);
    }
  } finally {
    clearTimeout(safetyTimeout);
    showLoading(false);
  }
}

// Load basic analytics as fallback
async function loadBasicAnalytics() {
  try {
    console.log('📊 Loading basic analytics fallback...');
    
    // Try to get just the summary data
    const response = await fetch(`${API_BASE_URL}/api/summary`, {
      credentials: 'include'
    });
    
    if (response.ok) {
      const result = await response.json();
      if (result.success) {
        // Show basic summary without charts
        updateSummaryCards({
          total_spent: result.total_spent || 0,
          average_daily: result.average_daily || 0,
          daily_budget_limit: result.daily_limit || 30,
          days_over_budget: result.days_over_budget || 0
        });
        
        // Show a simple message instead of charts
        const chartContainer = document.getElementById('spendingChart');
        if (chartContainer) {
          chartContainer.innerHTML = '<div class="no-data">Basic analytics loaded. Charts unavailable.</div>';
        }
        
        console.log('✅ Basic analytics loaded successfully');
      }
    }
  } catch (error) {
    console.error('❌ Basic analytics fallback failed:', error);
    throw error;
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
  
  // Budget limit
  const budgetLimitEl = document.getElementById('budgetLimit');
  if (budgetLimitEl) {
    budgetLimitEl.textContent = `$${summary.daily_budget_limit.toFixed(2)}`;
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
  
  // Add mobile-specific CSS class to chart container
  const chartContainer = ctx.parentElement;
  if (chartContainer) {
    chartContainer.classList.add('daily-spending-chart');
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
  
  // Detect mobile device and orientation
  const isMobile = window.innerWidth <= 768;
  const isSmallMobile = window.innerWidth <= 480;
  const isLandscape = window.innerHeight < window.innerWidth && isMobile;
  
  // Mobile-specific chart configurations
  const pointRadius = isLandscape ? 2 : (isSmallMobile ? 3 : (isMobile ? 4 : 6));
  const pointHoverRadius = isLandscape ? 3 : (isSmallMobile ? 4 : (isMobile ? 6 : 8));
  const borderWidth = isLandscape ? 1 : (isMobile ? 2 : 3);
  const titleFontSize = isLandscape ? 10 : (isSmallMobile ? 12 : (isMobile ? 14 : 18));
  const legendFontSize = isLandscape ? 8 : (isSmallMobile ? 10 : (isMobile ? 12 : 14));
  const axisFontSize = isLandscape ? 8 : (isSmallMobile ? 10 : (isMobile ? 12 : 14));
  
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
          borderWidth: borderWidth,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#4CAF50',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 1,
          pointRadius: pointRadius,
          pointHoverRadius: pointHoverRadius
        },
        {
          label: 'Budget Limit',
          data: budgetLineData,
          borderColor: '#FF6B6B',
          backgroundColor: 'transparent',
          borderWidth: isMobile ? 1 : 2,
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
            size: titleFontSize,
            weight: 'bold'
          },
          color: '#ffffff'
        },
        legend: {
          display: true,
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: isLandscape ? 5 : (isMobile ? 10 : 20),
            font: {
              size: legendFontSize
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
              // Parse the date string correctly to avoid timezone issues (same as chart labels)
              const [year, month, day] = data[dataIndex].date.split('-');
              const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
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
              size: axisFontSize,
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
              size: axisFontSize,
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
    console.log(`🔄 Loading overlay ${show ? 'shown' : 'hidden'}`);
  } else {
    console.error('❌ Loading overlay element not found!');
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

// Load category breakdown data
async function loadCategoryData() {
  try {
    const timeRange = document.getElementById('timeRange').value;
    const urlParams = new URLSearchParams(window.location.search);
    const dayOffset = urlParams.get('dayOffset') || '0';
    
    console.log('🔄 Fetching category breakdown data...');
    const response = await fetch(`${API_BASE_URL}/api/analytics/category-breakdown?days=${timeRange}&dayOffset=${dayOffset}`, {
      credentials: 'include',
      headers: {
        'Cache-Control': 'no-cache'
      }
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Category API Error Response:', errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('🥧 Category data received:', result);
    
    if (result.success) {
      createCategoryChart(result.data, result.summary);
    } else {
      throw new Error(result.error || 'Failed to load category data');
    }
    
  } catch (error) {
    console.error('❌ Error loading category data:', error);
    showError('Failed to load category breakdown data.');
  }
}

// Create category breakdown pie chart
function createCategoryChart(data, summary) {
  const ctx = document.getElementById('categoryChart');
  if (!ctx) return;
  
  // Add mobile-specific CSS class to chart container
  const chartContainer = ctx.parentElement;
  if (chartContainer) {
    chartContainer.classList.add('category-chart');
  }
  
  // Destroy existing chart
  if (categoryChart) {
    console.log('🗑️ Destroying existing category chart');
    categoryChart.destroy();
    categoryChart = null;
  }
  
  if (!data || data.length === 0) {
    // Show empty state
    ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
    const legendEl = document.getElementById('categoryLegend');
    if (legendEl) {
      legendEl.innerHTML = '<p class="no-data">No spending data available for the selected period.</p>';
    }
    return;
  }
  
  // Prepare chart data
  const labels = data.map(item => item.category);
  const amounts = data.map(item => item.amount);
  const colors = data.map(item => item.color);
  
  // Chart configuration
  const config = {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: amounts,
        backgroundColor: colors,
        borderColor: colors.map(color => color),
        borderWidth: 2,
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false // We'll create custom legend
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const item = data[context.dataIndex];
              return `${item.category}: $${item.amount.toFixed(2)} (${item.percentage}%)`;
            }
          }
        }
      },
      animation: {
        animateRotate: true,
        animateScale: true,
        duration: 1000
      }
    }
  };
  
  // Create chart
  categoryChart = new Chart(ctx, config);
  
  // Create custom legend
  createCategoryLegend(data, summary);
  
  console.log('🥧 Category chart created successfully');
}

// Create custom category legend
function createCategoryLegend(data, summary) {
  const legendEl = document.getElementById('categoryLegend');
  if (!legendEl) return;
  
  if (!data || data.length === 0) {
    legendEl.innerHTML = '<p class="no-data">No spending data available for the selected period.</p>';
    return;
  }
  
  let legendHTML = '<div class="legend-grid">';
  
  data.forEach(item => {
    const percentage = item.percentage;
    const amount = item.amount;
    const count = item.count;
    
    legendHTML += `
      <div class="legend-item">
        <div class="legend-color" style="background-color: ${item.color}"></div>
        <div class="legend-details">
          <div class="legend-category">${item.category}</div>
          <div class="legend-stats">
            <span class="legend-amount">$${amount.toFixed(2)}</span>
            <span class="legend-percentage">(${percentage}%)</span>
            <span class="legend-count">${count} transaction${count !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>
    `;
  });
  
  legendHTML += '</div>';
  
  // Add summary
  legendHTML += `
    <div class="legend-summary">
      <div class="summary-item">
        <span class="summary-label">Total Categories:</span>
        <span class="summary-value">${summary.total_categories}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Total Spent:</span>
        <span class="summary-value">$${summary.total_spent.toFixed(2)}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Period:</span>
        <span class="summary-value">${summary.days_analyzed} days</span>
      </div>
    </div>
  `;
  
  legendEl.innerHTML = legendHTML;
}

// Load heatmap data
async function loadHeatmapData() {
  try {
    const timeRange = document.getElementById('timeRange').value;
    const urlParams = new URLSearchParams(window.location.search);
    const dayOffset = urlParams.get('dayOffset') || '0';
    
    // Use the timeRange directly as days (the backend expects days parameter)
    const days = parseInt(timeRange);
    
    console.log('🔄 Fetching heatmap data...');
    const response = await fetch(`${API_BASE_URL}/api/analytics/weekly-heatmap?days=${days}&dayOffset=${dayOffset}`, {
      credentials: 'include',
      headers: {
        'Cache-Control': 'no-cache'
      }
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Heatmap API Error Response:', errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('🔥 Heatmap data received:', result);
    
    if (result.success) {
      createHeatmap(result.data, result.summary);
    } else {
      throw new Error(result.error || 'Failed to load heatmap data');
    }
    
  } catch (error) {
    console.error('❌ Error loading heatmap data:', error);
    showError('Failed to load weekly heatmap data.');
  }
}

// Create 30-day spending heatmap
function createHeatmap(data, summary) {
  const gridEl = document.getElementById('heatmapGrid');
  const summaryEl = document.getElementById('heatmapSummary');
  
  if (!gridEl || !summaryEl) return;
  
  // Add mobile-specific CSS class to heatmap container
  const heatmapContainer = gridEl.closest('.heatmap-container') || gridEl.parentElement;
  if (heatmapContainer) {
    heatmapContainer.classList.add('heatmap-chart');
  }
  
  if (!data || data.length === 0) {
    gridEl.innerHTML = '<p class="no-data">No spending data available for the selected period.</p>';
    summaryEl.innerHTML = '';
    return;
  }
  
  // Create day headers (Mon, Tue, Wed, etc.)
  const dayHeaders = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  
  let gridHTML = '<div class="heatmap-table">';
  
  // Add cleaner day headers
  gridHTML += '<div class="heatmap-header">';
  gridHTML += '<div class="week-label-header">Week</div>'; // Cleaner header
  dayHeaders.forEach(day => {
    gridHTML += `<div class="day-header">${day}</div>`;
  });
  gridHTML += '</div>';
  
  // Add weeks with actual dates
  data.forEach((week, weekIndex) => {
    gridHTML += '<div class="heatmap-week">';
    
    // Show the date range for this week instead of "Week X"
    const firstDay = week.find(day => day.date);
    const lastDay = week.filter(day => day.date).pop();
    
    let weekLabel = '';
    if (firstDay && lastDay) {
      if (firstDay.month_name === lastDay.month_name) {
        // Same month: "Jan 1-7"
        weekLabel = `${firstDay.month_name} ${firstDay.day_number}-${lastDay.day_number}`;
      } else {
        // Different months: "Dec 30 - Jan 5"
        weekLabel = `${firstDay.month_name} ${firstDay.day_number} - ${lastDay.month_name} ${lastDay.day_number}`;
      }
    }
    
    gridHTML += `<div class="week-label">${weekLabel}</div>`;
    
    week.forEach(day => {
      if (day.date) {
        const tooltip = `${day.month_name} ${day.day_number}: $${day.amount} (${day.count} transaction${day.count !== 1 ? 's' : ''})`;
        gridHTML += `
          <div class="heatmap-day level-${day.color_level}" 
               data-date="${day.date}" 
               data-amount="${day.amount}" 
               data-count="${day.count}"
               data-month="${day.month_name}"
               title="${tooltip}">
            <span class="day-number">${day.day_number}</span>
          </div>
        `;
      } else {
        gridHTML += '<div class="heatmap-day empty"></div>';
      }
    });
    
    gridHTML += '</div>';
  });
  
  gridHTML += '</div>';
  
  gridEl.innerHTML = gridHTML;
  
  // Create summary
  const summaryHTML = `
    <div class="heatmap-stats">
      <div class="stat-item">
        <span class="stat-label">Period:</span>
        <span class="stat-value">${summary.total_days} days</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Max Daily:</span>
        <span class="stat-value">$${summary.max_spending}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Avg Daily:</span>
        <span class="stat-value">$${summary.avg_spending}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Date Range:</span>
        <span class="stat-value">${summary.start_date} to ${summary.end_date}</span>
      </div>
    </div>
  `;
  
  summaryEl.innerHTML = summaryHTML;
  
  // Add click handlers for day details
  const dayElements = gridEl.querySelectorAll('.heatmap-day[data-date]');
  dayElements.forEach(dayEl => {
    dayEl.addEventListener('click', function() {
      const date = this.dataset.date;
      const amount = parseFloat(this.dataset.amount);
      const count = parseInt(this.dataset.count);
      
      if (amount > 0) {
        showDayDetails(date, amount, count);
      }
    });
  });
  
  console.log('🔥 Heatmap created successfully');
}

// Show day details modal
function showDayDetails(date, amount, count) {
  const dateObj = new Date(date);
  const formattedDate = dateObj.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  
  const modal = document.createElement('div');
  modal.className = 'day-details-modal';
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3>${formattedDate}</h3>
        <button class="modal-close">&times;</button>
      </div>
      <div class="modal-body">
        <div class="day-summary">
          <div class="summary-item">
            <span class="summary-label">Total Spent:</span>
            <span class="summary-value">$${amount.toFixed(2)}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Transactions:</span>
            <span class="summary-value">${count}</span>
          </div>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Close modal handlers
  const closeBtn = modal.querySelector('.modal-close');
  closeBtn.addEventListener('click', () => modal.remove());
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });
  
  // Auto-close after 3 seconds
  setTimeout(() => {
    if (modal.parentElement) modal.remove();
  }, 3000);
}

// Handle window resize
window.addEventListener('resize', function() {
  if (spendingChart) {
    spendingChart.resize();
  }
  if (categoryChart) {
    categoryChart.resize();
  }
});


console.log('📊 Analytics JavaScript loaded successfully');