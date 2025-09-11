// Utility: Get dayOffset from query string
function getDayOffset() {
  const params = new URLSearchParams(window.location.search);
  return parseInt(params.get('dayOffset') || '0', 10);
}

// Get API base URL - works for both local development and production
function getApiBaseUrl() {
  // In production, API will be served from the same origin
  // In development, detect if we're running on a different port than the API
  const isDevelopment = window.location.hostname === 'localhost' && window.location.port !== '';
  const isLivereload = window.location.port === '8080' || window.location.port === '3000'; // Common dev ports
  
  if (isDevelopment && isLivereload) {
    // Use environment variable if available, otherwise default to 5001
    const apiPort = window.ENV_API_PORT || '5001';
    return `http://localhost:${apiPort}`;
  }
  
  // In production, API is served from same origin
  return '';
}

const dayOffset = getDayOffset();
const API_BASE_URL = getApiBaseUrl();

// Global debug mode flag
let DEBUG_MODE = false;

// Fetch application configuration
async function fetchConfig() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/config`, {
      credentials: 'include'
    });
    
    if (response.ok) {
      const config = await response.json();
      DEBUG_MODE = config.debug || false;
      console.log('🔧 Debug mode:', DEBUG_MODE);
    } else {
      console.warn('⚠️ Could not fetch config, defaulting to debug mode off');
      DEBUG_MODE = false;
    }
  } catch (error) {
    console.warn('⚠️ Error fetching config:', error);
    DEBUG_MODE = false;
  }
}

// Debug API URL detection
console.log('🔍 API URL Debug:');
console.log('  Hostname:', window.location.hostname);
console.log('  Port:', window.location.port);
console.log('  API_BASE_URL:', API_BASE_URL);
console.log('  Full URL:', window.location.href);

// DOM Elements
const app = document.getElementById('app');

// Authentication Functions
function checkAuthentication() {
  // For session-based auth, we'll make an API call to verify the session
  return fetch(`${API_BASE_URL}/api/auth/me`, {
    credentials: 'include'
  }).then(response => {
    if (response.ok) {
      return response.json().then(data => {
        // Store user info in localStorage for UI display
        localStorage.setItem('sprout_user', JSON.stringify(data.user));
        return true;
      });
    } else {
      // Clear any stale user data
      localStorage.removeItem('sprout_user');
      // Redirect to auth page
      window.location.href = '/auth.html';
      return false;
    }
  }).catch(() => {
    // Network error or server down
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
    // Even if the API call fails, clear local storage and redirect
    localStorage.removeItem('sprout_user');
    window.location.href = '/auth.html';
  });
}

function getCurrentUser() {
  const userData = localStorage.getItem('sprout_user');
  return userData ? JSON.parse(userData) : null;
}

// Category management
let categories = [];
let isLoadingCategories = false;
let categoryBudgets = null;
let userCategoryPreference = true; // Default to requiring categories

// Load user's category preference
async function loadCategoryPreference() {
  try {
    console.log('🔄 Loading category preference...');
    const response = await fetch(`${API_BASE_URL}/api/preferences/category-requirement`, {
      credentials: 'include'
    });
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        userCategoryPreference = data.require_categories;
        console.log('✅ Category preference loaded:', userCategoryPreference);
      }
    }
  } catch (error) {
    console.warn('⚠️ Failed to load category preference, using default (required):', error);
    userCategoryPreference = true; // Default to requiring categories
  }
}

// Load categories from API
async function loadCategories() {
  if (isLoadingCategories || categories.length > 0) return;
  
  console.log('🔄 Loading categories...');
  isLoadingCategories = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/categories`, {
      credentials: 'include'
    });
    console.log('📡 Categories API response:', response.status, response.ok);
    if (response.ok) {
      categories = await response.json();
      console.log('✅ Categories loaded:', categories.length, 'categories');
      console.log('📋 Categories data:', categories);
    } else {
      console.error('❌ Categories API failed:', response.status);
    }
  } catch (error) {
    console.error('💥 Categories load error:', error);
  } finally {
    isLoadingCategories = false;
  }
}

// Load category budget tracking data
async function loadCategoryBudgets() {
  try {
    console.log('🔄 Loading category budgets...');
    const response = await fetch(`${API_BASE_URL}/api/categories/budget-tracking?dayOffset=${dayOffset}`, {
      credentials: 'include'
    });
    if (response.ok) {
      const responseText = await response.text();
      console.log('📡 Raw API response:', responseText);
      
      try {
        categoryBudgets = JSON.parse(responseText);
        console.log('✅ Category budgets loaded:', categoryBudgets);
        console.log('📊 Budgeted categories count:', categoryBudgets?.budgeted_categories?.length || 0);
        if (categoryBudgets?.budgeted_categories) {
          categoryBudgets.budgeted_categories.forEach(cat => {
            console.log(`   ${cat.category_name}: $${cat.daily_budget} budget, $${cat.spent_today} spent, $${cat.remaining_today} remaining`);
          });
        }
      } catch (parseError) {
        console.error('❌ Failed to parse JSON response:', parseError);
        categoryBudgets = null;
      }
    } else {
      console.error('❌ Category budgets API failed:', response.status);
      categoryBudgets = null;
    }
  } catch (error) {
    console.error('💥 Category budgets load error:', error);
    categoryBudgets = null;
  }
}

// Render compact category budget indicators for hero section
function renderCompactCategoryBudgets() {
  console.log('🔍 renderCompactCategoryBudgets called');
  console.log('📊 categoryBudgets:', categoryBudgets);
  
  if (!categoryBudgets || !categoryBudgets.budgeted_categories || categoryBudgets.budgeted_categories.length === 0) {
    console.log('❌ No budgeted categories to show');
    return ''; // No budgeted categories to show
  }

  const budgetedCategories = categoryBudgets.budgeted_categories;
  const categoryItems = budgetedCategories.map(cat => {
    const isOverBudget = cat.is_over_budget;
    const displayAmount = Math.abs(cat.remaining_today).toFixed(2);
    
    console.log(`🎨 Rendering budget for ${cat.category_name}: remaining_today=${cat.remaining_today}, displayAmount=${displayAmount}`);
    
    return `
      <div class="compact-budget-item ${isOverBudget ? 'over-budget' : ''}">
        <span class="compact-icon">${cat.category_icon}</span>
        <span class="compact-name">${cat.category_name}</span>
        <span class="compact-amount ${isOverBudget ? 'negative' : ''}">${isOverBudget ? '-' : ''}$${displayAmount}</span>
      </div>
    `;
  }).join('');

  return `
    <div class="compact-budgets">
      ${categoryItems}
    </div>
  `;
}



// Render main UI
function renderMainUI(summary) {
  const compactBudgetsHtml = renderCompactCategoryBudgets();
  const currentUser = getCurrentUser();
  
  app.innerHTML = `
    <div class="container">
      <!-- Logo Header -->
      <div class="logo-container">
        <img src="image.png" alt="Sprout Logo" class="logo">
        ${currentUser ? `
          <div class="user-info">
            <span class="username">Welcome, ${currentUser.email}!</span>
            <button onclick="logout()" class="btn btn-small">Logout</button>
          </div>
        ` : ''}
      </div>
      
      <!-- Compact Date Simulation Controls (Top Right) - Only in Debug Mode -->
      ${DEBUG_MODE ? `
      <div class="compact-date-controls">
        <div class="date-display-compact">
          <span id="current-date-value" class="current-date-value-compact">Loading...</span>
        </div>
        <div class="date-controls-compact">
          <button id="prev-day-btn" class="btn btn-tiny btn-secondary" title="Previous Day">←</button>
          <button id="next-day-btn" class="btn btn-tiny btn-secondary" title="Next Day">→</button>
          <button id="reset-date-btn" class="btn btn-tiny btn-primary" title="Reset to Today">Today</button>
        </div>
      </div>
      ` : ''}
      
      <!-- Main Content Grid -->
      <div class="main-grid">

        <!-- Hero Section - Balance and Plant Status -->
        <div class="hero-section">
          <div class="hero-content">
            <div class="balance-display">💵 $${summary.balance.toFixed(2)}</div>
            <div class="balance-subtitle">Left Today</div>
            
            ${compactBudgetsHtml ? `<div class="balance-breakdown">${compactBudgetsHtml}</div>` : ''}
            
            <div class="plant-status">
              <div class="plant-emoji" title="${summary.plant_state}">${summary.plant_emoji}</div>
              <div class="plant-text">${getPlantStatusText(summary.plant_state)}</div>
            </div>
          </div>
        </div>

        <!-- Stats Sidebar -->
        <div class="stats-sidebar">
          <div class="projection-card">
            <div class="projection-header">30-Day Projection</div>
            <div class="projection-amount">${summary.projection_30 >= 0 ? '+' : ''}$${summary.projection_30.toFixed(2)}</div>
          </div>
          
          <!-- Navigation in Sidebar -->
          <div class="sidebar-nav">
            <a href="history.html${window.location.search}" class="btn btn-secondary btn-full">📊 View History</a>
            <a href="analytics.html" class="btn btn-secondary btn-full">📈 Analytics</a>
            <a href="budgets.html" class="btn btn-secondary btn-full">💰 Budgets</a>
            <a href="recurring-expenses.html" class="btn btn-secondary btn-full">🔄 Recurring</a>
            <a href="settings.html" class="btn btn-secondary btn-full">⚙️ Settings</a>
    </div>
    </div>
    </div>

      <!-- Add Expense Form -->
    <div id="add-expense-container"></div>
    </div>
  `;
}

// Get plant status text based on state
function getPlantStatusText(state) {
  const statusMap = {
    'thriving': 'Growing Strong',
    'healthy': 'Flourishing',
    'struggling': 'Needs Care',
    'wilting': 'Over Budget Today',
    'dead': 'Way Over Budget'
  };
  return statusMap[state] || 'Budget Status';
}

// Render add expense form
async function renderAddExpenseForm() {
  console.log('🏗️ Rendering add expense form...');
  const container = document.getElementById('add-expense-container');
  console.log('📊 dayOffset:', dayOffset);
  
  if (dayOffset !== 0) {
    console.log('⚠️ Form disabled for past days');
    container.innerHTML = `
      <div class="form-section">
        <div class="disabled-message">Add Expense feature is disabled for past days</div>
      </div>
    `;
    return;
  }
  
  // Load categories and user preferences first
  console.log('📂 Loading categories for form...');
  await loadCategories();
  await loadCategoryPreference();
  console.log('📂 Categories after loading:', categories.length);
  console.log('📂 Category preference:', userCategoryPreference);
  
  // Build category options
  const categoryOptions = categories.map(cat => 
    `<option value="${cat.id}">${cat.icon} ${cat.name}</option>`
  ).join('');
  console.log('🔧 Built category options:', categoryOptions);
  
  // Determine category field requirements based on user preference
  const categoryRequired = userCategoryPreference ? 'required' : '';
  const categoryPlaceholder = userCategoryPreference ? 'Select Category (Required)' : 'Select Category (Optional)';
  
  container.innerHTML = `
    <div class="form-section">
      <div class="form-header">Add New Expense</div>
      <form id="add-expense-form">
        <div class="form-grid">
          <div class="form-group">
            <input 
              name="amount" 
              type="number" 
              min="0.01" 
              step="0.01" 
              placeholder="Amount ($)" 
              required 
              class="form-input"
            >
          </div>
          <div class="form-group">
            <input 
              name="description" 
              type="text" 
              placeholder="Description (optional)" 
              class="form-input"
            >
          </div>
          <div class="form-group category-group">
            <select name="category" class="form-input category-select" ${categoryRequired}>
              <option value="">${categoryPlaceholder}</option>
              ${categoryOptions}
            </select>
          </div>
          <button type="submit" class="btn btn-primary">Add Expense</button>
        </div>
    </form>
      
      <div id="add-expense-error"></div>
    </div>
  `;
  


  document.getElementById('add-expense-form').onsubmit = async (e) => {
    e.preventDefault();
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const errorDiv = document.getElementById('add-expense-error');
    
    const amount = parseFloat(form.amount.value);
    const description = form.description.value;
    const categoryId = form.category.value || null; // Keep as string, don't parse to int
    
    if (!amount || amount <= 0) {
      errorDiv.innerHTML = `
        <div class="status-message status-error">
          <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
            <span style="font-size: 16px;">⚠️</span>
            <span>Please enter a valid amount greater than $0.</span>
          </div>
        </div>
      `;
      return;
    }
    
    // Debug: Log the current preference state
    console.log('🔍 Form submission debug:');
    console.log('  userCategoryPreference:', userCategoryPreference);
    console.log('  categoryId:', categoryId);
    console.log('  should require category:', userCategoryPreference && !categoryId);
    
    if (userCategoryPreference && !categoryId) {
      errorDiv.innerHTML = `
        <div class="status-message status-error">
          <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
            <span style="font-size: 16px;">⚠️</span>
            <span>Category is required</span>
          </div>
        </div>
      `;
      return;
    }
    
    // Show loading state
    submitButton.textContent = 'Adding Expense...';
    submitButton.disabled = true;
    errorDiv.innerHTML = `
      <div class="status-message status-info">
        <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
          <span style="font-size: 16px;">⏳</span>
          <span>Adding your expense...</span>
        </div>
      </div>
    `;
    
    try {
      // Prepare request body
      const requestBody = { 
        amount, 
        description,
        category_id: categoryId
      };
      
    // POST to API
      const resp = await fetch(`${API_BASE_URL}/api/expenses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
        body: JSON.stringify(requestBody)
    });
      
    if (resp.ok) {
        console.log('✅ Expense added successfully!');
        
        // Enhanced success message with better UX
        const successMessage = `
          <div class="status-message status-success" style="background: rgba(0, 200, 81, 0.15); border: 2px solid rgba(0, 200, 81, 0.4); padding: 12px 16px; font-weight: 600;">
            <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
              <span style="font-size: 18px;">✅</span>
              <span style="font-size: 14px;">SUCCESS! Expense added successfully! Your budget has been updated.</span>
            </div>
          </div>
        `;
        errorDiv.innerHTML = successMessage;
        
        // Add a brief flash effect to make success more noticeable
        setTimeout(() => {
          const messageElement = errorDiv.querySelector('.status-message');
          if (messageElement) {
            messageElement.style.transform = 'scale(1.02)';
            messageElement.style.transition = 'transform 0.2s ease-out';
            setTimeout(() => {
              messageElement.style.transform = 'scale(1)';
            }, 200);
          }
        }, 100);
        
        // Success - refresh summary and reset form
        try {
          await loadSummaryWithFallbacks();
        } catch (summaryError) {
          console.warn('Summary refresh failed, but expense was added:', summaryError);
        }
      form.reset();
        
        // Auto-hide after 5 seconds with fade effect (longer to ensure visibility)
        setTimeout(() => {
          const messageElement = errorDiv.querySelector('.status-message');
          if (messageElement) {
            messageElement.style.transition = 'opacity 0.5s ease-out';
            messageElement.style.opacity = '0';
            setTimeout(() => errorDiv.innerHTML = '', 500);
          }
        }, 5000);
        
        // Focus back to amount field for quick entry of next expense
        setTimeout(() => {
          const amountInput = form.querySelector('input[name="amount"]');
          if (amountInput) amountInput.focus();
        }, 100);
        
    } else {
        try {
      const err = await resp.json();
          const message = err.demo_mode ? 'Demo mode - expenses not saved to database' : (err.error || 'Unable to add expense. Please try again.');
          errorDiv.innerHTML = `
            <div class="status-message status-error">
              <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
                <span style="font-size: 16px;">❌</span>
                <span>${message}</span>
              </div>
            </div>
          `;
        } catch (parseError) {
          errorDiv.innerHTML = `
            <div class="status-message status-error">
              <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
                <span style="font-size: 16px;">❌</span>
                <span>Unable to add expense. Please try again.</span>
              </div>
            </div>
          `;
        }
      }
    } catch (networkError) {
      errorDiv.innerHTML = `
        <div class="status-message status-error">
          <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
            <span style="font-size: 16px;">🌐</span>
            <span>Network error. Please check your connection and try again.</span>
          </div>
        </div>
      `;
    } finally {
      // Reset button state
      submitButton.textContent = 'Add Expense';
      submitButton.disabled = false;
    }
  };
}

// Render offline/error UI
function renderOfflineUI() {
  app.innerHTML = `
    <div class="container">
      <!-- Logo Header -->
      <div class="logo-container">
        <img src="image.png" alt="Sprout Logo" class="logo">
      </div>
      
      <!-- Status Bar -->
      <div class="status-bar">
        <div class="status-indicator">
          <span class="status-dot offline"></span>
          <span class="status-text">Offline Mode</span>
        </div>
      </div>

      <!-- Main Content Grid -->
      <div class="main-grid">
        <!-- Hero Section - Balance and Plant Status -->
        <div class="hero-section">
          <div class="hero-content">
            <div class="balance-display">💵 $30.00</div>
            <div class="balance-subtitle">Left Today</div>
            <div class="balance-mode">Default Budget</div>
            
            <div class="plant-status">
              <div class="plant-emoji" title="healthy">🌱</div>
              <div class="plant-text">Growing Strong</div>
            </div>
          </div>
        </div>

        <!-- Stats Sidebar -->
        <div class="stats-sidebar">
          <div class="projection-card">
            <div class="projection-header">30-Day Projection</div>
            <div class="projection-amount">+$900.00</div>
          </div>
          
          <!-- Navigation in Sidebar -->
          <div class="sidebar-nav">
            <a href="history.html${window.location.search}" class="btn btn-secondary btn-full">📊 View History</a>
            <a href="analytics.html" class="btn btn-secondary btn-full">📈 Analytics</a>
            <a href="budgets.html" class="btn btn-secondary btn-full">💰 Budgets</a>
            <a href="recurring-expenses.html" class="btn btn-secondary btn-full">🔄 Recurring</a>
            <a href="settings.html" class="btn btn-secondary btn-full">⚙️ Settings</a>
          </div>
        </div>
      </div>

      <!-- Add Expense Form -->
      <div id="add-expense-container"></div>
    </div>
  `;
}

// Simple test to ensure JavaScript is running
console.log('🌱 Sprout Budget Tracker JavaScript loaded');

// Fallback render function that always works
function renderFallbackUI() {
  const app = document.getElementById('app');
  if (!app) {
    console.error('App element not found!');
    return;
  }
  
  app.innerHTML = `
    <div class="container">
      <!-- Logo Header -->
      <div class="logo-container">
        <img src="image.png" alt="Sprout Logo" class="logo">
      </div>
      
      <!-- Status Bar -->
      <div class="status-bar">
        <div class="status-indicator">
          <span class="status-dot demo"></span>
          <span class="status-text">Demo Mode</span>
        </div>
      </div>

      <!-- Main Content Grid -->
      <div class="main-grid">
        <!-- Hero Section - Balance and Plant Status -->
        <div class="hero-section">
          <div class="hero-content">
            <div class="balance-display">💵 $30.00</div>
            <div class="balance-subtitle">Left Today</div>
            
            <div class="plant-status">
              <div class="plant-emoji" title="healthy">🌱</div>
              <div class="plant-text">Growing Strong</div>
            </div>
          </div>
        </div>

        <!-- Stats Sidebar -->
        <div class="stats-sidebar">
          <div class="projection-card">
            <div class="projection-header">30-Day Projection</div>
            <div class="projection-amount">+$900.00</div>
          </div>
          
          <!-- Navigation in Sidebar -->
          <div class="sidebar-nav">
            <a href="history.html" class="btn btn-secondary btn-full">📊 View History</a>
            <a href="budgets.html" class="btn btn-secondary btn-full">💰 Budgets</a>
            <a href="recurring-expenses.html" class="btn btn-secondary btn-full">🔄 Recurring</a>
            <a href="settings.html" class="btn btn-secondary btn-full">⚙️ Settings</a>
          </div>
        </div>
      </div>

      <!-- Demo Form -->
      <div class="form-section">
        <div class="form-header">Add New Expense</div>
        <div class="form-grid">
          <div class="form-group">
            <input type="number" min="0.01" step="0.01" placeholder="Amount ($)" class="form-input">
          </div>
          <div class="form-group">
            <input type="text" placeholder="Description (optional)" class="form-input">
          </div>
                      <button onclick="showDemoMessage()" class="btn btn-primary">Add Expense</button>
        </div>
      </div>
      
      <!-- Debug Section -->
      <div class="form-section" style="margin-top: 20px; border: 2px solid #ff6b6b;">
        <div class="form-header" style="color: #ff6b6b;">🔧 Debug Tools</div>
        <div class="form-grid">
          <button onclick="testSummaryAPI()" class="btn btn-secondary">Test Summary API</button>
          <button onclick="testAuthAPI()" class="btn btn-secondary">Test Auth API</button>
          <button onclick="clearConsole()" class="btn btn-secondary">Clear Console</button>
        </div>
      </div>
    </div>
  `;
  console.log('✅ Fallback UI rendered');
}

// Demo message function for fallback UI
function showDemoMessage() {
  const event = document.createElement('div');
  event.innerHTML = '<div class="status-message status-warning">Expense saved! (Demo mode - not actually saved)</div>';
  event.style.position = 'fixed';
  event.style.top = '20px';
  event.style.left = '50%';
  event.style.transform = 'translateX(-50%)';
  event.style.zIndex = '1000';
  document.body.appendChild(event);
  setTimeout(() => event.remove(), 3000);
}

// Enhanced load summary with multiple fallbacks
async function loadSummaryWithFallbacks() {
  console.log('🔄 Starting loadSummaryWithFallbacks...');
  console.log('📍 API_BASE_URL:', API_BASE_URL);
  console.log('📍 Current URL:', window.location.href);
  
  // First check authentication
  try {
    console.log('🔒 Checking authentication...');
    const isAuthenticated = await checkAuthentication();
    if (!isAuthenticated) {
      console.log('🔒 Authentication failed, redirecting...');
      return; // Will redirect to auth page
    }
    console.log('✅ Authentication successful');
  } catch (error) {
    console.error('🔒 Authentication check failed:', error);
    return;
  }
  
  try {
    console.log('🌐 Attempting API call to /api/summary...');
    const summaryUrl = `${API_BASE_URL}/api/summary?dayOffset=${dayOffset}`;
    console.log('📍 Summary URL:', summaryUrl);
    
    const resp = await fetch(summaryUrl, {
      credentials: 'include'
    });
    
    console.log('📡 Summary response status:', resp.status, resp.statusText);
    
    if (!resp.ok) {
      if (resp.status === 401) {
        console.log('🔒 Session expired, redirecting to login...');
        logout();
        return;
      }
      throw new Error(`API returned ${resp.status}: ${resp.statusText}`);
    }
    
  const summary = await resp.json();
    console.log('✅ API call successful, summary data:', summary);
    
    // Load rollover budget data if available
    try {
      const rolloverResponse = await fetch(`${API_BASE_URL}/api/rollover/current-budget`, {
        credentials: 'include'
      });
      
      if (rolloverResponse.ok) {
        const rolloverData = await rolloverResponse.json();
        console.log('✅ Rollover budget loaded:', rolloverData);
        
        if (rolloverData.success && rolloverData.rollover_enabled) {
          // Use effective budget (base + rollover) instead of regular balance
          summary.balance = rolloverData.effective_budget;
          summary.rollover_info = {
            base_budget: rolloverData.base_daily_limit,
            rollover_amount: rolloverData.rollover_amount,
            effective_budget: rolloverData.effective_budget
          };
          console.log('🔄 Using rollover-aware budget:', summary.balance);
        }
      }
    } catch (rolloverError) {
      console.warn('⚠️ Could not load rollover data, using regular budget:', rolloverError);
    }
    
    // Load category budgets first
    await loadCategoryBudgets();
    
    // Now render the main UI with budget data
  renderMainUI(summary);
  renderAddExpenseForm();
  
  // Setup date simulation controls (only in debug mode)
  if (DEBUG_MODE) {
    setupDateSimulationControls();
  }
    
  } catch (error) {
    console.error('❌ API call failed with error:', error.message);
    console.error('❌ Full error:', error);
    console.warn('⚠️ Falling back to offline UI...');
    
    try {
      renderOfflineUI();
      renderAddExpenseForm();
      console.log('✅ Offline UI rendered');
    } catch (offlineError) {
      console.error('❌ Offline UI failed, using fallback:', offlineError.message);
      renderFallbackUI();
    }
  }
}



// Initialize app with config first
async function initApp() {
  // Fetch config first to set debug mode
  await fetchConfig();
  
  // Then load the summary and render the UI
  await loadSummaryWithFallbacks();
}

// On page load - wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
} 

// Force deployment refresh - production fix for blank screen issue

// Debug functions
async function testSummaryAPI() {
  console.log('🧪 Testing Summary API...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/summary`, {
      credentials: 'include'
    });
    console.log('📡 Summary API Response:', response.status, response.statusText);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Summary API Success:', data);
      alert('✅ Summary API working! Check console for details.');
    } else {
      console.error('❌ Summary API Error:', response.status, response.statusText);
      alert(`❌ Summary API failed: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    console.error('💥 Summary API Exception:', error);
    alert(`💥 Summary API Exception: ${error.message}`);
  }
}

async function testAuthAPI() {
  console.log('🧪 Testing Auth API...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      credentials: 'include'
    });
    console.log('📡 Auth API Response:', response.status, response.statusText);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Auth API Success:', data);
      alert('✅ Auth API working! Check console for details.');
    } else {
      console.error('❌ Auth API Error:', response.status, response.statusText);
      alert(`❌ Auth API failed: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    console.error('💥 Auth API Exception:', error);
    alert(`💥 Auth API Exception: ${error.message}`);
  }
}

function clearConsole() {
  console.clear();
  console.log('🧹 Console cleared');
  alert('Console cleared!');
}

// ==========================================
// DATE SIMULATION FUNCTIONS
// ==========================================

function setupDateSimulationControls() {
  console.log('🗓️ Setting up date simulation controls...');
  
  // Load current date
  loadCurrentDate();
  
  // Add event listeners
  const prevDayBtn = document.getElementById('prev-day-btn');
  const nextDayBtn = document.getElementById('next-day-btn');
  const resetDateBtn = document.getElementById('reset-date-btn');
  
  if (prevDayBtn) {
    prevDayBtn.addEventListener('click', () => navigateDate(-1));
  }
  
  if (nextDayBtn) {
    nextDayBtn.addEventListener('click', () => navigateDate(1));
  }
  
  if (resetDateBtn) {
    resetDateBtn.addEventListener('click', resetToToday);
  }
  
  console.log('✅ Date simulation controls setup complete');
}

async function loadCurrentDate() {
  try {
    console.log('📅 Loading current date...');
    const response = await fetch(`${API_BASE_URL}/api/preferences/date-simulation`, {
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    console.log('📅 Date simulation data:', data);
    
    const dateValueElement = document.getElementById('current-date-value');
    if (dateValueElement) {
      if (data.is_simulated && data.simulated_date) {
        dateValueElement.textContent = data.simulated_date;
        dateValueElement.classList.add('simulated');
      } else {
        const today = new Date().toISOString().split('T')[0];
        dateValueElement.textContent = today;
        dateValueElement.classList.remove('simulated');
      }
    }
    
  } catch (error) {
    console.error('❌ Error loading current date:', error);
    const dateValueElement = document.getElementById('current-date-value');
    if (dateValueElement) {
      const today = new Date().toISOString().split('T')[0];
      dateValueElement.textContent = today;
      dateValueElement.classList.remove('simulated');
    }
  }
}

async function navigateDate(direction) {
  try {
    const currentDateElement = document.getElementById('current-date-value');
    const currentDate = currentDateElement.textContent;
    
    if (!currentDate || currentDate === 'Loading...') {
      console.error('❌ No current date available');
      return;
    }
    
    const date = new Date(currentDate);
    date.setDate(date.getDate() + direction);
    const newDate = date.toISOString().split('T')[0];
    
    console.log(`📅 Navigating from ${currentDate} to ${newDate} (${direction > 0 ? 'next' : 'previous'} day)`);
    
    await setSimulatedDate(newDate);
    
  } catch (error) {
    console.error('❌ Error navigating date:', error);
  }
}

async function resetToToday() {
  try {
    console.log('📅 Resetting to today...');
    
    const response = await fetch(`${API_BASE_URL}/api/preferences/date-simulation`, {
      method: 'DELETE',
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    console.log('📅 Reset date response:', data);
    
    if (data.success) {
      const today = new Date().toISOString().split('T')[0];
      const dateValueElement = document.getElementById('current-date-value');
      if (dateValueElement) {
        dateValueElement.textContent = today;
        dateValueElement.classList.remove('simulated');
      }
      
      // Reload the page to refresh all data with the new date
      window.location.reload();
    } else {
      throw new Error(data.error || 'Failed to reset date');
    }
    
  } catch (error) {
    console.error('❌ Error resetting to today:', error);
  }
}

async function setSimulatedDate(date) {
  try {
    console.log('📅 Setting simulated date to:', date);
    
    const response = await fetch(`${API_BASE_URL}/api/preferences/date-simulation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify({
        simulated_date: date
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    console.log('📅 Set date response:', data);
    
    if (data.success) {
      const dateValueElement = document.getElementById('current-date-value');
      if (dateValueElement) {
        dateValueElement.textContent = data.simulated_date;
        dateValueElement.classList.add('simulated');
      }
      
      // Reload the page to refresh all data with the new date
      window.location.reload();
    } else {
      throw new Error(data.error || 'Failed to set simulated date');
    }
    
  } catch (error) {
    console.error('❌ Error setting simulated date:', error);
  }
} 