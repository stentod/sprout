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
const historyRoot = document.getElementById('history');

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

// Global state
let categories = [];
let currentPeriod = 7;
let currentCategoryId = null;

// Load categories from API
async function loadCategories() {
  if (categories.length > 0) return;
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/categories`, {
      credentials: 'include'
    });
    if (response.status === 401) {
      console.log('🔒 Session expired, redirecting to login...');
      logout();
      return;
    }
    if (response.ok) {
      categories = await response.json();
      console.log('Loaded categories in history.js:', categories);
    }
  } catch (error) {
    console.error('Error loading categories:', error);
    categories = [];
  }
}

// Render filters UI
function renderFilters() {
  const categoryOptions = categories.map(cat => 
    `<option value="${cat.id}" ${currentCategoryId == cat.id ? 'selected' : ''}>${cat.icon} ${cat.name}</option>`
  ).join('');

  return `
    <div class="filters-container">
      <div class="filter-group">
        <label for="period-filter">Period:</label>
        <select id="period-filter" class="filter-select">
          <option value="7" ${currentPeriod === 7 ? 'selected' : ''}>Last 7 Days</option>
          <option value="30" ${currentPeriod === 30 ? 'selected' : ''}>Last 30 Days</option>
          <option value="90" ${currentPeriod === 90 ? 'selected' : ''}>Last 3 Months</option>
          <option value="180" ${currentPeriod === 180 ? 'selected' : ''}>Last 6 Months</option>
        </select>
      </div>
      
      <div class="filter-group">
        <label for="category-filter">Category:</label>
        <select id="category-filter" class="filter-select">
          <option value="" ${!currentCategoryId ? 'selected' : ''}>All Categories</option>
          ${categoryOptions}
        </select>
      </div>
      
      <button id="clear-filters" class="btn btn-secondary">Clear Filters</button>
    </div>
  `;
}

// Render history with modern UI
function renderHistory(days) {
  const periodText = currentPeriod === 7 ? '7 Days' : 
                    currentPeriod === 30 ? '30 Days' : 
                    currentPeriod === 90 ? '3 Months' : '6 Months';
  
  const selectedCategory = currentCategoryId ? 
    categories.find(cat => cat.id == currentCategoryId) : null;
  
  const titleSuffix = selectedCategory ? 
    ` - ${selectedCategory.icon} ${selectedCategory.name}` : '';

  let html = `
    <div class="history-container">
      <div class="history-header">
        <h1>📊 Expense History - Last ${periodText}${titleSuffix}</h1>
        <div class="history-nav">
          <a href="index.html${window.location.search}" class="btn btn-primary">🏠 Back to Today</a>
          <a href="analytics.html" class="btn btn-secondary">📈 Analytics</a>
          <a href="settings.html" class="btn btn-secondary">⚙️ Settings</a>
        </div>
      </div>
      
      ${renderFilters()}
      
      <div class="history-content">
  `;

  if (days.length === 0) {
    html += `
      <div class="no-expenses">
        <div class="no-expenses-icon">💸</div>
        <div class="no-expenses-text">No expenses found${selectedCategory ? ` for ${selectedCategory.name}` : ''}</div>
        <div class="no-expenses-subtext">Try adjusting your filters or add some expenses!</div>
      </div>
    `;
  } else {
    // Calculate stats
    const totalSpent = days.reduce((sum, day) => 
      sum + day.expenses.reduce((daySum, exp) => daySum + exp.amount, 0), 0);
    const totalExpenses = days.reduce((sum, day) => sum + day.expenses.length, 0);
    const dailyAverage = totalSpent / currentPeriod;

    html += `
      <div class="stats-summary">
        <div class="stat-card">
          <div class="stat-value">$${totalSpent.toFixed(2)}</div>
          <div class="stat-label">Total Spent</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${totalExpenses}</div>
          <div class="stat-label">Total Expenses</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">$${dailyAverage.toFixed(2)}</div>
          <div class="stat-label">Daily Average</div>
        </div>
      </div>
    `;

    for (const day of days) {
      const dateObj = new Date(day.date + 'T00:00:00');
      const dateStr = dateObj.toLocaleDateString(undefined, { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
      });
      
      const dayTotal = day.expenses.reduce((sum, exp) => sum + exp.amount, 0);
      
      html += `
        <div class="day-section">
          <div class="day-header">
            <span class="day-date">📅 ${dateStr}</span>
            <span class="day-total">$${dayTotal.toFixed(2)}</span>
          </div>
          <div class="expenses-list">
      `;

      for (const exp of day.expenses) {
        console.log('Expense data:', exp); // Debug log
        const categoryInfo = exp.category ? 
          `<span class="expense-category" style="color: ${exp.category.color}">${exp.category.icon} ${exp.category.name}</span>` :
          `<span class="expense-category no-category">📝 Uncategorized</span>`;
        
        html += `
          <div class="expense-item">
            <div class="expense-main">
              <span class="expense-amount">$${exp.amount.toFixed(2)}</span>
              <span class="expense-description">${exp.description || 'No description'}</span>
            </div>
            <div class="expense-meta">
              ${categoryInfo}
            </div>
            <div class="expense-actions">
              <button class="edit-expense-btn" data-expense-id="${exp.id}" data-amount="${exp.amount}" data-description="${exp.description}" data-category-id="${exp.category ? (exp.category.is_default ? 'default_' + exp.category.id : 'custom_' + exp.category.id) : 'none'}" data-category-type="${exp.category ? (exp.category.is_default ? 'default' : 'custom') : 'none'}">✏️ Edit</button>
              <button class="delete-expense-btn" data-expense-id="${exp.id}">🗑️ Delete</button>
            </div>
          </div>
        `;
      }

      html += `
          </div>
        </div>
      `;
    }
  }

  html += `
      </div>
    </div>
  `;

  historyRoot.innerHTML = html;
  
  // Setup event handlers
  setupEventHandlers();
}

// Setup event handlers for filters and expense actions
function setupEventHandlers() {
  const periodFilter = document.getElementById('period-filter');
  const categoryFilter = document.getElementById('category-filter');
  const clearFiltersBtn = document.getElementById('clear-filters');

  if (periodFilter) {
    periodFilter.addEventListener('change', (e) => {
      currentPeriod = parseInt(e.target.value);
      loadHistory();
    });
  }

  if (categoryFilter) {
    categoryFilter.addEventListener('change', (e) => {
      currentCategoryId = e.target.value || null;
      loadHistory();
    });
  }

  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
      currentPeriod = 7;
      currentCategoryId = null;
      loadHistory();
    });
  }

  // Add event delegation for edit and delete buttons
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('edit-expense-btn')) {
      const expenseId = e.target.dataset.expenseId;
      const amount = e.target.dataset.amount;
      const description = e.target.dataset.description;
      const categoryId = e.target.dataset.categoryId === 'none' ? '' : e.target.dataset.categoryId;
      const categoryType = e.target.dataset.categoryType;
      console.log('Button clicked - categoryId:', categoryId, 'categoryType:', categoryType);
      editExpense(expenseId, amount, description, categoryId);
    } else if (e.target.classList.contains('delete-expense-btn')) {
      const expenseId = e.target.dataset.expenseId;
      deleteExpense(expenseId);
    }
  });
}

// Load history with current filters
async function loadHistory() {
  try {
    // Load categories first
    await loadCategories();
    
    // Build API URL with filters
    let url = `${API_BASE_URL}/api/history?dayOffset=${dayOffset}&period=${currentPeriod}`;
    if (currentCategoryId) {
      url += `&category_id=${currentCategoryId}`;
    }
    
    const resp = await fetch(url, {
      credentials: 'include'
    });
    if (resp.status === 401) {
      console.log('🔒 Session expired, redirecting to login...');
      logout();
      return;
    }
    if (!resp.ok) {
      throw new Error(`API returned ${resp.status}`);
    }
    const days = await resp.json();
    renderHistory(days);
  } catch (error) {
    console.warn('API unavailable, showing offline message:', error.message);
    
    historyRoot.innerHTML = `
      <div class="history-container">
        <div class="history-header">
          <h1>📊 Expense History</h1>
        </div>
        <div class="error-message">
          <div class="error-icon">⚠️</div>
          <div class="error-text">Database connection unavailable</div>
          <div class="error-subtext">History will be available when deployed with a database.</div>
          <div class="error-actions">
            <a href="index.html${window.location.search}" class="btn btn-primary">🏠 Back to Today</a>
          </div>
        </div>
      </div>
    `;
  }
}

// Edit expense functionality
async function editExpense(expenseId, amount, description, categoryId) {
  console.log('editExpense called with:', { expenseId, amount, description, categoryId });
  try {
    // Load categories first to ensure we have them for the dropdown
    await loadCategories();
    
    // Create modal HTML
    const modalHtml = `
      <div class="edit-modal" id="editModal">
        <div class="edit-modal-content">
          <div class="edit-modal-header">
            <h3>✏️ Edit Expense</h3>
            <button class="close-modal-btn">&times;</button>
          </div>
          <form id="editExpenseForm">
            <div class="form-group">
              <label for="editAmount">Amount ($):</label>
              <input type="number" id="editAmount" name="amount" step="0.01" min="0.01" value="${amount}" required>
            </div>
            <div class="form-group">
              <label for="editDescription">Description:</label>
              <input type="text" id="editDescription" name="description" value="${description || ''}" required>
            </div>
            <div class="form-group">
              <label for="editCategory">Category:</label>
              <select id="editCategory" name="category_id">
                <option value="">No Category</option>
                ${categories.map(cat => {
                  // Check if cat.id already has the prefix
                  let catValue;
                  if (typeof cat.id === 'string' && (cat.id.startsWith('default_') || cat.id.startsWith('custom_'))) {
                    // cat.id already has the prefix, use it as-is
                    catValue = cat.id;
                  } else {
                    // cat.id is numeric, construct the prefix
                    catValue = cat.is_default ? 'default_' + cat.id : 'custom_' + cat.id;
                  }
                  
                  const isSelected = categoryId === catValue;
                  console.log('Category comparison:', { 
                    catValue, 
                    categoryId, 
                    isSelected, 
                    catName: cat.name,
                    catId: cat.id,
                    catIsDefault: cat.is_default,
                    comparison: `${categoryId} === ${catValue}`,
                    catIdType: typeof cat.id
                  });
                  return `<option value="${catValue}" ${isSelected ? 'selected' : ''}>${cat.icon} ${cat.name}</option>`;
                }).join('')}
              </select>
            </div>
            <div class="form-actions">
              <button type="button" class="cancel-edit-btn">Cancel</button>
              <button type="submit" class="save-edit-btn">Save Changes</button>
            </div>
          </form>
        </div>
      </div>
    `;
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    const modal = document.getElementById('editModal');
    modal.style.display = 'block';
    
    // Setup modal event handlers
    const closeBtn = modal.querySelector('.close-modal-btn');
    const cancelBtn = modal.querySelector('.cancel-edit-btn');
    const form = modal.querySelector('#editExpenseForm');
    
    closeBtn.addEventListener('click', () => {
      modal.remove();
    });
    
    cancelBtn.addEventListener('click', () => {
      modal.remove();
    });
    
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const formData = new FormData(form);
      const categoryId = formData.get('category_id');
      const updateData = {
        amount: parseFloat(formData.get('amount')),
        description: formData.get('description'),
        category_id: categoryId && categoryId.trim() !== '' ? categoryId : null
      };
      
      console.log('Sending update data:', updateData);
      try {
        const response = await fetch(`${API_BASE_URL}/api/expenses/${expenseId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(updateData)
        });
        
        if (response.ok) {
          showSuccessMessage('Expense updated successfully!');
          modal.remove();
          loadHistory(); // Refresh the history
        } else {
          const errorData = await response.json();
          showErrorMessage(`Failed to update expense: ${errorData.message || 'Unknown error'}`);
        }
      } catch (error) {
        showErrorMessage(`Failed to update expense: ${error.message}`);
      }
    });
    
  } catch (error) {
    console.error('Error setting up edit modal:', error);
    showErrorMessage('Failed to open edit form');
  }
}

// Delete expense functionality
async function deleteExpense(expenseId) {
  if (!confirm('Are you sure you want to delete this expense? This action cannot be undone.')) {
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/expenses/${expenseId}`, {
      method: 'DELETE',
      credentials: 'include'
    });
    
    if (response.ok) {
      showSuccessMessage('Expense deleted successfully!');
      loadHistory(); // Refresh the history
    } else {
      const errorData = await response.json();
      showErrorMessage(`Failed to delete expense: ${errorData.message || 'Unknown error'}`);
    }
  } catch (error) {
    showErrorMessage(`Failed to delete expense: ${error.message}`);
  }
}

// Show success message
function showSuccessMessage(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'success-message';
  messageDiv.textContent = message;
  document.body.appendChild(messageDiv);
  
  setTimeout(() => {
    messageDiv.remove();
  }, 3000);
}

// Show error message
function showErrorMessage(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'error-message';
  messageDiv.textContent = message;
  document.body.appendChild(messageDiv);
  
  setTimeout(() => {
    messageDiv.remove();
  }, 3000);
}

// Initialize the page with authentication check
async function initializePage() {
  try {
    const isAuthenticated = await checkAuthentication();
    if (isAuthenticated) {
      loadHistory();
    }
  } catch (error) {
    console.error('Authentication check failed:', error);
    window.location.href = '/auth.html';
  }
}

initializePage(); 