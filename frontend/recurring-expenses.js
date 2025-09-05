// Recurring Expenses page JavaScript
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
let recurringExpenseForm;
let descriptionInput;
let amountInput;
let categorySelect;
let frequencySelect;
let startDateInput;
let processBtn;
let setupTableBtn;
let formStatusMessage;
let expensesContainer;
let expensesStatusMessage;

// State
let categories = [];
let recurringExpenses = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Recurring expenses page loaded');
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
    recurringExpenseForm = document.getElementById('recurring-expense-form');
    descriptionInput = document.getElementById('description');
    amountInput = document.getElementById('amount');
    categorySelect = document.getElementById('category');
    frequencySelect = document.getElementById('frequency');
    startDateInput = document.getElementById('start-date');
    formStatusMessage = document.getElementById('form-status-message');
    expensesContainer = document.getElementById('recurring-expenses-container');
    expensesStatusMessage = document.getElementById('expenses-status-message');
    
    // Set default start date to today (in local timezone)
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    startDateInput.value = `${year}-${month}-${day}`;
    
    // Load data and set up event listeners
    await Promise.all([
        loadCategories(),
        loadRecurringExpenses()
    ]);
    
    setupEventListeners();
});

function setupEventListeners() {
    // Form submission
    recurringExpenseForm.addEventListener('submit', handleFormSubmit);
}

async function loadCategories() {
    try {
        console.log('Loading categories...');
        const response = await fetch(`${API_BASE}/categories`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Categories loaded:', data);
        
        // Handle both old and new category response formats
        if (data.success && data.categories) {
            categories = data.categories;
        } else if (Array.isArray(data)) {
            categories = data;
        } else {
            throw new Error('Invalid categories response format');
        }
        
        renderCategoryOptions();
        
    } catch (error) {
        console.error('Error loading categories:', error);
        showFormStatusMessage('Failed to load categories. Please refresh the page.', 'error');
    }
}

function renderCategoryOptions() {
    categorySelect.innerHTML = '<option value="">Select a category (optional)</option>';
    
    categories.forEach(category => {
        const option = document.createElement('option');
        // category.id already has the prefix from the API (default_123 or custom_456)
        option.value = category.id;
        option.textContent = `${category.icon} ${category.name}`;
        categorySelect.appendChild(option);
    });
}

async function loadRecurringExpenses() {
    try {
        console.log('Loading recurring expenses...');
        const response = await fetch(`${API_BASE}/recurring-expenses`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Recurring expenses loaded:', data);
        
        if (data.success) {
            recurringExpenses = data.recurring_expenses;
            renderRecurringExpenses();
        } else {
            throw new Error(data.error || 'Failed to load recurring expenses');
        }
        
    } catch (error) {
        console.error('Error loading recurring expenses:', error);
        showExpensesStatusMessage('Failed to load recurring expenses. Please refresh the page.', 'error');
    }
}

function renderRecurringExpenses() {
    if (recurringExpenses.length === 0) {
        expensesContainer.innerHTML = `
            <div class="empty-state">
                <p>No recurring expenses yet. Add one above to get started!</p>
            </div>
        `;
        return;
    }
    
    expensesContainer.innerHTML = recurringExpenses.map(expense => `
        <div class="expense-item ${!expense.is_active ? 'inactive' : ''}">
            <div class="expense-info">
                <div class="expense-header">
                    <h3 class="expense-description">${expense.description}</h3>
                    <span class="expense-amount">$${expense.amount.toFixed(2)}</span>
                </div>
                <div class="expense-details">
                    <span class="expense-frequency">${getFrequencyText(expense.frequency)}</span>
                    ${expense.category ? `<span class="expense-category">${expense.category.icon} ${expense.category.name}</span>` : ''}
                    <span class="expense-date">Starts: ${formatDate(expense.start_date)}</span>
                </div>
            </div>
            <div class="expense-actions">
                <button class="btn btn-danger btn-sm" onclick="deleteRecurringExpense(${expense.id})">
                    🗑️ Delete
                </button>
            </div>
        </div>
    `).join('');
}

function getFrequencyText(frequency) {
    const frequencyMap = {
        'daily': 'Daily',
        'weekly': 'Weekly',
        'monthly': 'Monthly'
    };
    return frequencyMap[frequency] || frequency;
}

function formatDate(dateString) {
    // Parse the date string as local date to avoid timezone issues
    const [year, month, day] = dateString.split('-');
    const date = new Date(year, month - 1, day); // month is 0-indexed
    return date.toLocaleDateString();
}

async function handleFormSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(recurringExpenseForm);
    const expenseData = {
        description: formData.get('description').trim(),
        amount: parseFloat(formData.get('amount')),
        category_id: formData.get('category') || null,
        frequency: formData.get('frequency'),
        start_date: formData.get('start_date')
    };
    
    // Validation
    if (!expenseData.description) {
        showFormStatusMessage('Please enter a description.', 'error');
        return;
    }
    
    if (expenseData.amount <= 0) {
        showFormStatusMessage('Please enter a valid amount.', 'error');
        return;
    }
    
    if (!expenseData.frequency) {
        showFormStatusMessage('Please select a frequency.', 'error');
        return;
    }
    
    try {
        console.log('Creating recurring expense:', expenseData);
        
        const response = await fetch(`${API_BASE}/recurring-expenses`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(expenseData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Create recurring expense response:', data);
        
        if (data.success) {
            showFormStatusMessage('Recurring expense created successfully!', 'success');
            recurringExpenseForm.reset();
            startDateInput.value = new Date().toISOString().split('T')[0];
            await loadRecurringExpenses();
        } else {
            throw new Error(data.error || 'Failed to create recurring expense');
        }
        
    } catch (error) {
        console.error('Error creating recurring expense:', error);
        showFormStatusMessage(`Failed to create recurring expense: ${error.message}`, 'error');
    }
}

async function deleteRecurringExpense(expenseId) {
    if (!confirm('Are you sure you want to delete this recurring expense?')) {
        return;
    }
    
    try {
        console.log('Deleting recurring expense:', expenseId);
        
        const response = await fetch(`${API_BASE}/recurring-expenses/${expenseId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Delete recurring expense response:', data);
        
        if (data.success) {
            showExpensesStatusMessage('Recurring expense deleted successfully!', 'success');
            await loadRecurringExpenses();
        } else {
            throw new Error(data.error || 'Failed to delete recurring expense');
        }
        
    } catch (error) {
        console.error('Error deleting recurring expense:', error);
        showExpensesStatusMessage(`Failed to delete recurring expense: ${error.message}`, 'error');
    }
}


function showFormStatusMessage(message, type) {
    formStatusMessage.textContent = message;
    formStatusMessage.className = `status-message ${type}`;
    formStatusMessage.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        formStatusMessage.style.display = 'none';
    }, 5000);
}

function showExpensesStatusMessage(message, type) {
    expensesStatusMessage.textContent = message;
    expensesStatusMessage.className = `status-message ${type}`;
    expensesStatusMessage.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        expensesStatusMessage.style.display = 'none';
    }, 5000);
}
