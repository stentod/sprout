// Settings page JavaScript
const API_BASE = window.location.hostname === 'localhost' && window.location.port !== '5001' 
    ? 'http://localhost:5001/api' 
    : '/api';

// Authentication Functions
function checkAuthentication() {
  console.log('🔒 Making auth request to:', `${API_BASE}/auth/me`);
  return fetch(`${API_BASE}/auth/me`, {
    credentials: 'include'
  }).then(response => {
    console.log('🔒 Auth response status:', response.status, response.statusText);
    if (response.ok) {
      return response.json().then(data => {
        console.log('🔒 Auth successful, user data:', data);
        localStorage.setItem('sprout_user', JSON.stringify(data.user));
        return true;
      });
    } else {
      console.log('🔒 Auth failed with status:', response.status);
      localStorage.removeItem('sprout_user');
      window.location.href = '/auth.html';
      return false;
    }
  }).catch((error) => {
    console.error('🔒 Auth request failed:', error);
    localStorage.removeItem('sprout_user');
    window.location.href = '/auth.html';
    return false;
  });
}

function logout() {
  fetch(`${API_BASE}/auth/logout`, {
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

// DOM elements
let dailyLimitForm;
let dailyLimitInput;
let currentLimitDisplay;
let statusMessage;
let saveButton;
let cancelButton;

// Category budget elements
let categoryBudgetsContainer;
let categoryStatusMessage;
let saveAllBudgetsButton;
let resetBudgetsButton;

// Category preference elements
let requireCategoriesToggle;
let preferenceStatusMessage;

// State
let originalLimit = 30.00;
let isLoading = false;
let categories = [];
let originalBudgets = {};
let currentBudgets = {};
let originalRequireCategories = true;

// Initialize the settings page
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Settings page loaded');
    console.log('📍 API_BASE:', API_BASE);
    console.log('📍 Current URL:', window.location.href);
    
    // Check authentication first
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
    
    // Get DOM elements
    dailyLimitForm = document.getElementById('daily-limit-form');
    dailyLimitInput = document.getElementById('daily-limit-input');
    currentLimitDisplay = document.getElementById('current-limit-display');
    statusMessage = document.getElementById('status-message');
    saveButton = document.getElementById('save-button');
    cancelButton = document.getElementById('cancel-button');
    
    // Category budget elements
    categoryBudgetsContainer = document.getElementById('category-budgets-container');
    categoryStatusMessage = document.getElementById('category-status-message');
    saveAllBudgetsButton = document.getElementById('save-all-budgets-button');
    resetBudgetsButton = document.getElementById('reset-budgets-button');
    
    // Category preference elements
    requireCategoriesToggle = document.getElementById('require-categories-toggle');
    preferenceStatusMessage = document.getElementById('preference-status-message');
    
    // Load current daily limit, categories, and preferences
    loadCurrentDailyLimit();
    loadCategories();
    loadCategoryPreference();
    
    // Set up event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Form submission
    dailyLimitForm.addEventListener('submit', handleFormSubmit);
    
    // Cancel button
    cancelButton.addEventListener('click', handleCancel);
    
    // Input validation
    dailyLimitInput.addEventListener('input', handleInputChange);
    
    // Category budget buttons
    saveAllBudgetsButton.addEventListener('click', handleSaveAllBudgets);
    resetBudgetsButton.addEventListener('click', handleResetBudgets);
    
    // Category preference toggle
    requireCategoriesToggle.addEventListener('change', handleCategoryPreferenceChange);
}

async function loadCurrentDailyLimit() {
    try {
        showLoading(true);
        clearStatusMessage();
        
        console.log('Loading current daily limit...');
        const response = await fetch(`${API_BASE}/preferences/daily-limit`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Daily limit data:', data);
        
        if (data.success) {
            originalLimit = data.daily_limit;
            updateCurrentLimitDisplay(originalLimit);
            dailyLimitInput.value = originalLimit.toFixed(2);
        } else {
            throw new Error(data.error || 'Failed to load daily limit');
        }
        
    } catch (error) {
        console.error('Error loading daily limit:', error);
        showStatusMessage('Failed to load current daily limit. Please refresh the page.', 'error');
    } finally {
        showLoading(false);
    }
}

async function handleFormSubmit(event) {
    event.preventDefault();
    
    if (isLoading) return;
    
    const newLimit = parseFloat(dailyLimitInput.value);
    
    // Validation
    if (isNaN(newLimit) || newLimit < 0) {
        showStatusMessage('Please enter a valid positive number.', 'error');
        return;
    }
    
    if (newLimit === originalLimit) {
        showStatusMessage('No changes to save.', 'info');
        return;
    }
    
    try {
        showLoading(true);
        clearStatusMessage();
        
        console.log('Saving new daily limit:', newLimit);
        
        const response = await fetch(`${API_BASE}/preferences/daily-limit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                daily_limit: newLimit
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Save response:', data);
        
        if (data.success) {
            originalLimit = data.daily_limit;
            updateCurrentLimitDisplay(originalLimit);
            showStatusMessage(data.message || 'Daily limit updated successfully!', 'success');
            
            // Reset form state
            dailyLimitInput.value = originalLimit.toFixed(2);
            
        } else {
            throw new Error(data.error || 'Failed to update daily limit');
        }
        
    } catch (error) {
        console.error('Error saving daily limit:', error);
        showStatusMessage('Failed to save daily limit. Please try again.', 'error');
    } finally {
        showLoading(false);
    }
}

function handleCancel() {
    // Reset form to original value
    dailyLimitInput.value = originalLimit.toFixed(2);
    clearStatusMessage();
    console.log('Form reset to original value:', originalLimit);
}

function handleInputChange() {
    // Clear status messages when user starts typing
    clearStatusMessage();
    
    // Update save button state
    const newValue = parseFloat(dailyLimitInput.value);
    const hasChanges = !isNaN(newValue) && newValue !== originalLimit;
    
    saveButton.textContent = hasChanges ? 'Save Changes' : 'No Changes';
    saveButton.disabled = !hasChanges;
}

function updateCurrentLimitDisplay(limit) {
    currentLimitDisplay.textContent = `$${limit.toFixed(2)}`;
    console.log('Updated current limit display:', limit);
}

function showLoading(loading) {
    isLoading = loading;
    saveButton.disabled = loading;
    cancelButton.disabled = loading;
    dailyLimitInput.disabled = loading;
    
    if (loading) {
        saveButton.textContent = 'Saving...';
    } else {
        const newValue = parseFloat(dailyLimitInput.value);
        const hasChanges = !isNaN(newValue) && newValue !== originalLimit;
        saveButton.textContent = hasChanges ? 'Save Changes' : 'No Changes';
        saveButton.disabled = !hasChanges;
    }
}

function showStatusMessage(message, type = 'info') {
    statusMessage.className = `status-message status-${type}`;
    statusMessage.textContent = message;
    statusMessage.style.display = 'block';
    
    console.log(`Status (${type}):`, message);
    
    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(clearStatusMessage, 3000);
    }
}

function clearStatusMessage() {
    statusMessage.style.display = 'none';
    statusMessage.textContent = '';
    statusMessage.className = 'status-message';
}

// Utility function to format currency
function formatCurrency(amount) {
    return `$${amount.toFixed(2)}`;
}

// ==========================================
// CATEGORY BUDGET MANAGEMENT
// ==========================================

async function loadCategories() {
    try {
        console.log('Loading categories...');
        categoryBudgetsContainer.innerHTML = '<div class="loading-message">Loading categories...</div>';
        
        const response = await fetch(`${API_BASE}/categories`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        categories = await response.json();
        console.log('Categories loaded:', categories.length);
        
        // Store original budgets
        originalBudgets = {};
        currentBudgets = {};
        categories.forEach(cat => {
            originalBudgets[cat.id] = cat.daily_budget;
            currentBudgets[cat.id] = cat.daily_budget;
        });
        
        renderCategoryBudgets();
        
    } catch (error) {
        console.error('Error loading categories:', error);
        categoryBudgetsContainer.innerHTML = '<div class="error-message">Failed to load categories. Please refresh the page.</div>';
    }
}

function renderCategoryBudgets() {
    if (!categories.length) {
        categoryBudgetsContainer.innerHTML = '<div class="no-categories">No categories found.</div>';
        return;
    }
    
    const html = categories.map(category => {
        const hasBudget = category.daily_budget > 0;
        const budgetValue = hasBudget ? category.daily_budget.toFixed(2) : '0.00';
        
        return `
        <div class="category-budget-item ${hasBudget ? 'has-budget' : 'no-budget'}" data-category-id="${category.id}">
            <div class="category-info">
                <div class="category-icon">${category.icon}</div>
                <div class="category-details">
                    <div class="category-name">${category.name}</div>
                    <div class="category-type">${category.is_default ? 'Default' : 'Custom'}</div>
                </div>
            </div>
            <div class="budget-controls">
                <div class="budget-toggle">
                    <label class="toggle-switch">
                        <input 
                            type="checkbox" 
                            class="budget-enable-checkbox"
                            data-category-id="${category.id}"
                            ${hasBudget ? 'checked' : ''}
                        >
                        <span class="toggle-slider"></span>
                    </label>
                    <span class="toggle-label">${hasBudget ? 'Budgeted' : 'No Budget'}</span>
                </div>
                <div class="budget-input-group ${hasBudget ? 'enabled' : 'disabled'}">
                    <div class="budget-input-wrapper">
                        <span class="currency-symbol">$</span>
                        <input 
                            type="number" 
                            class="category-budget-input"
                            data-category-id="${category.id}"
                            value="${budgetValue}"
                            step="0.01" 
                            min="0"
                            placeholder="0.00"
                            ${hasBudget ? '' : 'disabled'}
                        >
                        <span class="budget-unit">/day</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    }).join('');
    
    categoryBudgetsContainer.innerHTML = html;
    
    // Add event listeners to inputs and toggles
    const inputs = categoryBudgetsContainer.querySelectorAll('.category-budget-input');
    inputs.forEach(input => {
        input.addEventListener('input', handleCategoryBudgetChange);
    });
    
    const toggles = categoryBudgetsContainer.querySelectorAll('.budget-enable-checkbox');
    toggles.forEach(toggle => {
        toggle.addEventListener('change', handleBudgetToggle);
    });
}

function handleCategoryBudgetChange(event) {
    const categoryId = parseInt(event.target.dataset.categoryId);
    const newValue = parseFloat(event.target.value) || 0;
    
    currentBudgets[categoryId] = newValue;
    
    // Check if any budgets have changed
    const hasChanges = categories.some(cat => 
        currentBudgets[cat.id] !== originalBudgets[cat.id]
    );
    
    saveAllBudgetsButton.disabled = !hasChanges;
    saveAllBudgetsButton.textContent = hasChanges ? 'Save All Changes' : 'No Changes';
    
    clearCategoryStatusMessage();
}

function handleBudgetToggle(event) {
    const categoryId = parseInt(event.target.dataset.categoryId);
    const isEnabled = event.target.checked;
    const budgetItem = event.target.closest('.category-budget-item');
    const budgetInput = budgetItem.querySelector('.category-budget-input');
    const budgetInputGroup = budgetItem.querySelector('.budget-input-group');
    const toggleLabel = budgetItem.querySelector('.toggle-label');
    
    if (isEnabled) {
        // Enable budget for this category
        budgetItem.classList.remove('no-budget');
        budgetItem.classList.add('has-budget');
        budgetInputGroup.classList.remove('disabled');
        budgetInputGroup.classList.add('enabled');
        budgetInput.disabled = false;
        toggleLabel.textContent = 'Budgeted';
        
        // Set a default budget if it's currently 0
        if (parseFloat(budgetInput.value) === 0) {
            budgetInput.value = '10.00';
        }
        
        currentBudgets[categoryId] = parseFloat(budgetInput.value);
    } else {
        // Disable budget for this category
        budgetItem.classList.remove('has-budget');
        budgetItem.classList.add('no-budget');
        budgetInputGroup.classList.remove('enabled');
        budgetInputGroup.classList.add('disabled');
        budgetInput.disabled = true;
        toggleLabel.textContent = 'No Budget';
        
        currentBudgets[categoryId] = 0;
    }
    
    // Check if any budgets have changed
    const hasChanges = categories.some(cat => 
        currentBudgets[cat.id] !== originalBudgets[cat.id]
    );
    
    saveAllBudgetsButton.disabled = !hasChanges;
    saveAllBudgetsButton.textContent = hasChanges ? 'Save All Changes' : 'No Changes';
    
    clearCategoryStatusMessage();
}

async function handleSaveAllBudgets() {
    try {
        showCategoryLoading(true);
        clearCategoryStatusMessage();
        
        console.log('Saving category budgets:', currentBudgets);
        
        const response = await fetch(`${API_BASE}/categories/budgets`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                budgets: currentBudgets
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Save response:', data);
        
        if (data.success) {
            // Update original budgets to current ones
            originalBudgets = {...currentBudgets};
            
            showCategoryStatusMessage(
                data.message + (data.warnings ? ` (${data.warnings.length} warnings)` : ''), 
                data.warnings ? 'warning' : 'success'
            );
            
            if (data.warnings) {
                console.warn('Warnings:', data.warnings);
            }
            
        } else {
            throw new Error(data.error || 'Failed to update category budgets');
        }
        
    } catch (error) {
        console.error('Error saving category budgets:', error);
        showCategoryStatusMessage('Failed to save category budgets. Please try again.', 'error');
    } finally {
        showCategoryLoading(false);
    }
}

function handleResetBudgets() {
    // Reset all inputs to original values
    categories.forEach(cat => {
        const input = categoryBudgetsContainer.querySelector(`input[data-category-id="${cat.id}"]`);
        if (input) {
            input.value = originalBudgets[cat.id].toFixed(2);
            currentBudgets[cat.id] = originalBudgets[cat.id];
        }
    });
    
    saveAllBudgetsButton.disabled = true;
    saveAllBudgetsButton.textContent = 'No Changes';
    clearCategoryStatusMessage();
    
    console.log('Reset category budgets to original values');
}

function showCategoryLoading(loading) {
    saveAllBudgetsButton.disabled = loading;
    resetBudgetsButton.disabled = loading;
    
    const inputs = categoryBudgetsContainer.querySelectorAll('.category-budget-input');
    inputs.forEach(input => input.disabled = loading);
    
    if (loading) {
        saveAllBudgetsButton.textContent = 'Saving...';
    } else {
        const hasChanges = categories.some(cat => 
            currentBudgets[cat.id] !== originalBudgets[cat.id]
        );
        saveAllBudgetsButton.textContent = hasChanges ? 'Save All Changes' : 'No Changes';
        saveAllBudgetsButton.disabled = !hasChanges;
    }
}

function showCategoryStatusMessage(message, type = 'info') {
    categoryStatusMessage.className = `status-message status-${type}`;
    categoryStatusMessage.textContent = message;
    categoryStatusMessage.style.display = 'block';
    
    console.log(`Category Status (${type}):`, message);
    
    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(clearCategoryStatusMessage, 3000);
    }
}

function clearCategoryStatusMessage() {
    categoryStatusMessage.style.display = 'none';
    categoryStatusMessage.textContent = '';
    categoryStatusMessage.className = 'status-message';
}

// ==========================================
// CATEGORY PREFERENCE MANAGEMENT
// ==========================================

async function loadCategoryPreference() {
    try {
        console.log('Loading category preference...');
        
        const response = await fetch(`${API_BASE}/preferences/category-requirement`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Category preference data:', data);
        
        if (data.success) {
            originalRequireCategories = data.require_categories;
            requireCategoriesToggle.checked = originalRequireCategories;
        } else {
            throw new Error(data.error || 'Failed to load category preference');
        }
        
    } catch (error) {
        console.error('Error loading category preference:', error);
        // Default to true (categories required) if loading fails
        originalRequireCategories = true;
        requireCategoriesToggle.checked = true;
    }
}

async function handleCategoryPreferenceChange(event) {
    const newValue = event.target.checked;
    
    try {
        console.log('Saving category preference:', newValue);
        
        const response = await fetch(`${API_BASE}/preferences/category-requirement`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                require_categories: newValue
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Save preference response:', data);
        
        if (data.success) {
            originalRequireCategories = data.require_categories;
            showPreferenceStatusMessage(
                data.message || `Category requirement ${newValue ? 'enabled' : 'disabled'} successfully`, 
                'success'
            );
        } else {
            throw new Error(data.error || 'Failed to update category preference');
        }
        
    } catch (error) {
        console.error('Error saving category preference:', error);
        // Revert toggle to original state
        requireCategoriesToggle.checked = originalRequireCategories;
        
        // Show more detailed error message for debugging
        let errorMessage = 'Failed to update preference. Please try again.';
        if (error.message) {
            errorMessage += ` (${error.message})`;
        }
        showPreferenceStatusMessage(errorMessage, 'error');
    }
}

function showPreferenceStatusMessage(message, type = 'info') {
    preferenceStatusMessage.className = `status-message status-${type}`;
    preferenceStatusMessage.textContent = message;
    preferenceStatusMessage.style.display = 'block';
    
    console.log(`Preference Status (${type}):`, message);
    
    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(clearPreferenceStatusMessage, 3000);
    }
}

function clearPreferenceStatusMessage() {
    preferenceStatusMessage.style.display = 'none';
    preferenceStatusMessage.textContent = '';
    preferenceStatusMessage.className = 'status-message';
}

// ==========================================
// CUSTOM CATEGORY MANAGEMENT
// ==========================================

// Add category button event listener
document.getElementById('addCategory').addEventListener('click', function() {
    showAddCategoryModal();
});

function showAddCategoryModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <h2>Add Custom Category</h2>
            <form id="add-category-form">
                <div class="form-group">
                    <label for="category-name">Category Name</label>
                    <input type="text" id="category-name" name="name" class="form-input" required maxlength="100" placeholder="e.g., Coffee, Gym, etc.">
                </div>
                <div class="form-group">
                    <label for="category-icon">Icon</label>
                    <select id="category-icon" name="icon" class="form-input">
                        <option value="📦">📦 Other</option>
                        <option value="☕">☕ Coffee</option>
                        <option value="🏋️">🏋️ Gym</option>
                        <option value="🎮">🎮 Gaming</option>
                        <option value="📱">📱 Tech</option>
                        <option value="🎨">🎨 Art</option>
                        <option value="📚">📚 Books</option>
                        <option value="🎵">🎵 Music</option>
                        <option value="🍕">🍕 Pizza</option>
                        <option value="🚴">🚴 Cycling</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="category-color">Color</label>
                    <input type="color" id="category-color" name="color" class="form-input" value="#A9A9A9">
                </div>
                <div class="form-group">
                    <label for="category-budget">Daily Budget (Optional)</label>
                    <input type="number" id="category-budget" name="daily_budget" class="form-input" min="0" step="0.01" placeholder="0.00">
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Create Category</button>
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            </form>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Handle form submission
    document.getElementById('add-category-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const categoryData = {
            name: formData.get('name'),
            icon: formData.get('icon'),
            color: formData.get('color'),
            daily_budget: parseFloat(formData.get('daily_budget')) || 0
        };
        createCategory(categoryData);
    });
}

function closeModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
        modal.remove();
    }
}

async function createCategory(categoryData) {
    try {
        console.log('Creating custom category:', categoryData);
        
        const response = await fetch(`${API_BASE}/categories`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(categoryData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Create category response:', data);
        
        if (data.success) {
            showCategoryStatusMessage('Custom category created successfully!', 'success');
            closeModal();
            // Reload categories to show the new one
            await loadCategories();
            renderCategoryBudgets();
        } else {
            throw new Error(data.error || 'Failed to create category');
        }
        
    } catch (error) {
        console.error('Error creating category:', error);
        showCategoryStatusMessage(`Failed to create category: ${error.message}`, 'error');
    }
} 