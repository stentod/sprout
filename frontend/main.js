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

// DOM Elements
const app = document.getElementById('app');

// Category management
let categories = [];
let isLoadingCategories = false;

// Load categories from API
async function loadCategories() {
  if (isLoadingCategories || categories.length > 0) return;
  
  console.log('🔄 Loading categories...');
  isLoadingCategories = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/categories`);
    console.log('📡 Categories API response:', response.status, response.ok);
    if (response.ok) {
      categories = await response.json();
      console.log('✅ Categories loaded:', categories.length, 'categories');
      console.log('📋 Categories data:', categories);
    } else {
      console.error('❌ Categories API failed:', response.status);
    }
  } catch (error) {
    console.error('❌ Error loading categories:', error);
    categories = []; // Fallback to empty array
  } finally {
    isLoadingCategories = false;
  }
}



// Render main UI
function renderMainUI(summary) {
  app.innerHTML = `
    <div class="container">
      <!-- Main Content Grid -->
      <div class="main-grid">
        <!-- Hero Section - Balance and Plant Status -->
        <div class="hero-section">
          <div class="hero-content">
            <div class="balance-display">💵 $${summary.balance.toFixed(2)}</div>
            <div class="balance-subtitle">Left Today</div>
            
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
    'healthy': 'Growing Strong',
    'growing': 'Flourishing',
    'struggling': 'Needs Care',
    'wilting': 'Budget Stressed',
    'dead': 'Overspent'
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
  
  // Load categories first
  console.log('📂 Loading categories for form...');
  await loadCategories();
  console.log('📂 Categories after loading:', categories.length);
  
  // Build category options
  const categoryOptions = categories.map(cat => 
    `<option value="${cat.id}">${cat.icon} ${cat.name}</option>`
  ).join('');
  console.log('🔧 Built category options:', categoryOptions);
  
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
            <select name="category" class="form-input category-select" required>
              <option value="">Select Category (Required)</option>
              ${categoryOptions}
            </select>
          </div>
          <button type="submit" class="btn btn-primary">Save Expense</button>
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
    const categoryId = form.category.value ? parseInt(form.category.value) : null;
    
    if (!amount || amount <= 0) {
      errorDiv.innerHTML = '<div class="status-message status-error">Enter a valid amount.</div>';
      return;
    }
    
    if (!categoryId) {
      errorDiv.innerHTML = '<div class="status-message status-error">Please select a category for this expense.</div>';
      return;
    }
    
    // Show loading state
    submitButton.textContent = 'Saving...';
    submitButton.disabled = true;
    errorDiv.innerHTML = '';
    
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
        body: JSON.stringify(requestBody)
      });
      
      if (resp.ok) {
        // Success - refresh summary and reset form
        await loadSummaryWithFallbacks();
        form.reset();
        errorDiv.innerHTML = '<div class="status-message status-success">Expense saved successfully!</div>';
        setTimeout(() => errorDiv.innerHTML = '', 3000);
      } else {
        try {
          const err = await resp.json();
          const message = err.demo_mode ? 'Demo mode - expenses not saved to database' : (err.error || 'Error adding expense.');
          errorDiv.innerHTML = `<div class="status-message status-warning">${message}</div>`;
        } catch (parseError) {
          errorDiv.innerHTML = '<div class="status-message status-error">Error adding expense.</div>';
        }
      }
    } catch (networkError) {
      errorDiv.innerHTML = '<div class="status-message status-error">Network error. Please try again.</div>';
    } finally {
      // Reset button state
      submitButton.textContent = 'Save Expense';
      submitButton.disabled = false;
    }
  };
}

// Render offline/error UI
function renderOfflineUI() {
  app.innerHTML = `
    <div class="container">
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
          <button onclick="showDemoMessage()" class="btn btn-primary">Save Expense</button>
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
  
  try {
    console.log('🌐 Attempting API call...');
    const resp = await fetch(`${API_BASE_URL}/api/summary?dayOffset=${dayOffset}`);
    if (!resp.ok) {
      throw new Error(`API returned ${resp.status}`);
    }
    const summary = await resp.json();
    console.log('✅ API call successful, rendering main UI');
    renderMainUI(summary);
    renderAddExpenseForm();
  } catch (error) {
    console.warn('⚠️ API call failed, trying offline UI:', error.message);
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



// On page load - wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadSummaryWithFallbacks);
} else {
  loadSummaryWithFallbacks();
} 

// Force deployment refresh - production fix for blank screen issue 