// Settings page JavaScript
const API_BASE = 'http://localhost:5001/api';

// DOM elements
let dailyLimitForm;
let dailyLimitInput;
let currentLimitDisplay;
let statusMessage;
let saveButton;
let cancelButton;

// State
let originalLimit = 30.00;
let isLoading = false;

// Initialize the settings page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Settings page loaded');
    
    // Get DOM elements
    dailyLimitForm = document.getElementById('daily-limit-form');
    dailyLimitInput = document.getElementById('daily-limit-input');
    currentLimitDisplay = document.getElementById('current-limit-display');
    statusMessage = document.getElementById('status-message');
    saveButton = document.getElementById('save-button');
    cancelButton = document.getElementById('cancel-button');
    
    // Load current daily limit
    loadCurrentDailyLimit();
    
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
}

async function loadCurrentDailyLimit() {
    try {
        showLoading(true);
        clearStatusMessage();
        
        console.log('Loading current daily limit...');
        const response = await fetch(`${API_BASE}/preferences/daily-limit`);
        
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