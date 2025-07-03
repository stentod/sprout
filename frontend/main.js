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

// Render main UI
function renderMainUI(summary) {
  app.innerHTML = `
    <div style="text-align:center; margin-bottom:2rem;">
      <div style="font-size:3rem; font-weight:bold;">💵 $${summary.balance.toFixed(2)} Left Today</div>
    </div>
    <div style="text-align:center; font-size:4rem; margin-bottom:1rem;">
      <span title="${summary.plant_state}">${summary.plant_emoji}</span>
    </div>
    <div style="text-align:center; margin-bottom:2rem;">
      <span style="font-size:1.2rem;">📆 Projected 30-Day Balance: <b>${summary.projection_30 >= 0 ? '+' : ''}$${summary.projection_30.toFixed(2)}</b></span>
    </div>
    <div id="add-expense-container"></div>
    <div style="text-align:center; margin-top:2rem;">
      <a href="history.html${window.location.search}" style="background:#333;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px;">View History</a>
    </div>
  `;
}

// Render add expense form
function renderAddExpenseForm() {
  const container = document.getElementById('add-expense-container');
  if (dayOffset !== 0) {
    container.innerHTML = `<div style="text-align:center; color:#aaa; margin:2rem 0;">Add Expense disabled for past days</div>`;
    return;
  }
  container.innerHTML = `
    <form id="add-expense-form" style="max-width:320px;margin:2rem auto;">
      <input name="amount" type="number" min="0.01" step="0.01" placeholder="Amount ($)" required style="width:100%;padding:10px;margin-bottom:10px;background:#333;color:#fff;border:1px solid #555;border-radius:5px;">
      <input name="description" type="text" placeholder="Description (optional)" style="width:100%;padding:10px;margin-bottom:10px;background:#333;color:#fff;border:1px solid #555;border-radius:5px;">
      <button type="submit" style="width:100%;padding:10px;background:#4caf50;color:#fff;border:none;border-radius:5px;cursor:pointer;">Save Expense</button>
    </form>
    <div id="add-expense-error" style="color:#f55;text-align:center;margin-top:0.5rem;"></div>
  `;
  document.getElementById('add-expense-form').onsubmit = async (e) => {
    e.preventDefault();
    const form = e.target;
    const amount = parseFloat(form.amount.value);
    const description = form.description.value;
    if (!amount || amount <= 0) {
      document.getElementById('add-expense-error').textContent = 'Enter a valid amount.';
      return;
    }
    document.getElementById('add-expense-error').textContent = '';
    // POST to API
    const resp = await fetch(`${API_BASE_URL}/api/expenses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount, description })
    });
    if (resp.ok) {
      // Refresh summary
      loadSummary();
      form.reset();
    } else {
      const err = await resp.json();
      document.getElementById('add-expense-error').textContent = err.error || 'Error adding expense.';
    }
  };
}

// Load summary and render UI
async function loadSummary() {
  const resp = await fetch(`${API_BASE_URL}/api/summary?dayOffset=${dayOffset}`);
  const summary = await resp.json();
  renderMainUI(summary);
  renderAddExpenseForm();
}

// On page load
loadSummary(); 