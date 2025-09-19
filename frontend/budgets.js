// Budgets page JavaScript

// Get API base URL - works for both local development and production
function getApiBaseUrl() {
  const isDevelopment = window.location.hostname === 'localhost' && window.location.port !== '';
  const isLivereload = window.location.port === '8080' || window.location.port === '3000';
  
  if (isDevelopment && isLivereload) {
    const apiPort = window.ENV_API_PORT || '5001';
    return `http://localhost:${apiPort}`;
  }
  
  return '';
}

const API_BASE_URL = getApiBaseUrl();

// DOM Elements
const app = document.getElementById('app');

// Authentication Functions
function checkAuthentication() {
  return fetch(`${API_BASE_URL}/api/auth/me`, {
    credentials: 'include'
  }).then(response => {
    if (response.ok) {
      return response.json().then(data => {
        localStorage.setItem('sprout_user', JSON.stringify(data.user));
        return true;
      });
    } else {
      localStorage.removeItem('sprout_user');
      window.location.href = '/auth.html';
      return false;
    }
  }).catch(() => {
    console.warn('Unable to verify authentication, redirecting to auth page');
    localStorage.removeItem('sprout_user');
    window.location.href = '/auth.html';
    return false;
  });
}

function logout() {
  fetch(`${API_BASE_URL}/api/auth/logout`, {
    method: 'POST',
    credentials: 'include'
  }).then(() => {
    localStorage.removeItem('sprout_user');
    window.location.href = '/auth.html';
  }).catch(() => {
    localStorage.removeItem('sprout_user');
    window.location.href = '/auth.html';
  });
}

function getCurrentUser() {
  const userData = localStorage.getItem('sprout_user');
  return userData ? JSON.parse(userData) : null;
}

// Budget Functions
let budgetData = null;
let isLoading = false;

async function loadBudgets() {
  try {
    isLoading = true;
    updateLoadingState();
    
    const response = await fetch(`${API_BASE_URL}/api/preferences/budgets`, {
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    if (data.success) {
      budgetData = data;
      renderBudgets();
    } else {
      throw new Error(data.error || 'Failed to load budgets');
    }
  } catch (error) {
    console.error('Error loading budgets:', error);
    renderError('Failed to load budget data. Please try again.');
  } finally {
    isLoading = false;
    updateLoadingState();
  }
}

function updateLoadingState() {
  const loadingScreen = document.querySelector('.loading-screen');
  if (loadingScreen) {
    loadingScreen.style.display = isLoading ? 'flex' : 'none';
  }
}

function renderError(message) {
  app.innerHTML = `
    <div class="error-container">
      <div class="error-icon">⚠️</div>
      <div class="error-message">${message}</div>
      <button onclick="loadBudgets()" class="btn btn-primary">Retry</button>
      <a href="/" class="btn btn-secondary">Back to Home</a>
    </div>
  `;
}

function renderBudgets() {
  if (!budgetData) {
    renderError('No budget data available');
    return;
  }

  const user = getCurrentUser();
  const { daily_limit, budgets } = budgetData;
  
  app.innerHTML = `
    <div class="page-container">
      <!-- Header -->
      <div class="page-header">
        <div class="header-content">
          <h1>📊 Budget Overview</h1>
          <div class="header-actions">
            <span class="daily-limit-display">Daily Limit: $${daily_limit.toFixed(2)}</span>
            <a href="/" class="btn btn-secondary">🏠 Back to Home</a>
          </div>
        </div>
      </div>

      <!-- Budget Cards -->
      <div class="budget-grid">
        <!-- Weekly Budget -->
        <div class="budget-card weekly">
          <div class="budget-header">
            <h2>📅 Weekly Budget</h2>
            <div class="budget-period">Last 7 days</div>
          </div>
          <div class="budget-amounts">
            <div class="budget-total">$${budgets.weekly.budget.toFixed(2)}</div>
            <div class="budget-spent">$${budgets.weekly.spent.toFixed(2)} spent</div>
            <div class="budget-remaining">$${budgets.weekly.remaining.toFixed(2)} remaining</div>
          </div>
          <div class="budget-progress">
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${Math.min(budgets.weekly.percentage_used, 100)}%"></div>
            </div>
            <div class="progress-text">${budgets.weekly.percentage_used.toFixed(1)}% used</div>
          </div>
        </div>

        <!-- Monthly Budget -->
        <div class="budget-card monthly">
          <div class="budget-header">
            <h2>📆 Monthly Budget</h2>
            <div class="budget-period">Last 30 days</div>
          </div>
          <div class="budget-amounts">
            <div class="budget-total">$${budgets.monthly.budget.toFixed(2)}</div>
            <div class="budget-spent">$${budgets.monthly.spent.toFixed(2)} spent</div>
            <div class="budget-remaining">$${budgets.monthly.remaining.toFixed(2)} remaining</div>
          </div>
          <div class="budget-progress">
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${Math.min(budgets.monthly.percentage_used, 100)}%"></div>
            </div>
            <div class="progress-text">${budgets.monthly.percentage_used.toFixed(1)}% used</div>
          </div>
        </div>

        <!-- Yearly Budget -->
        <div class="budget-card yearly">
          <div class="budget-header">
            <h2>📊 Yearly Budget</h2>
            <div class="budget-period">Last 365 days</div>
          </div>
          <div class="budget-amounts">
            <div class="budget-total">$${budgets.yearly.budget.toFixed(2)}</div>
            <div class="budget-spent">$${budgets.yearly.spent.toFixed(2)} spent</div>
            <div class="budget-remaining">$${budgets.yearly.remaining.toFixed(2)} remaining</div>
          </div>
          <div class="budget-progress">
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${Math.min(budgets.yearly.percentage_used, 100)}%"></div>
            </div>
            <div class="progress-text">${budgets.yearly.percentage_used.toFixed(1)}% used</div>
          </div>
        </div>
      </div>


      <!-- Refresh Button -->
      <div class="refresh-section">
        <button onclick="loadBudgets()" class="btn btn-primary">🔄 Refresh Budgets</button>
      </div>
    </div>
  `;
}

// Initialize the budgets page
async function init() {
  try {
    console.log('Budgets page loaded');
    
    // Check authentication first
    const isAuthenticated = await checkAuthentication();
    if (!isAuthenticated) {
      return;
    }
    
    // Load budget data
    await loadBudgets();
    
  } catch (error) {
    console.error('Error initializing budgets page:', error);
    renderError('Failed to initialize page. Please refresh and try again.');
  }
}

// Start the app when DOM is loaded
document.addEventListener('DOMContentLoaded', init);
