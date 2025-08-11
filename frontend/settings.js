// Settings page JavaScript
const API_BASE = 'http://localhost:5001/api';

// Authentication Functions
function checkAuthentication() {
  return fetch(`${API_BASE}/auth/me`, {
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

// State
let originalLimit = 30.00;
let isLoading = false;
let categories = [];
let originalBudgets = {};
let currentBudgets = {};

// Initialize the settings page
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Settings page loaded');
    
    // Check authentication first
    try {
        const isAuthenticated = await checkAuthentication();
        if (!isAuthenticated) {
            console.log('🔒 Authentication failed, redirecting...');
            return; // Will redirect to auth page
        }
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
    
    // Load current daily limit and categories
    loadCurrentDailyLimit();
    loadCategories();
    
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