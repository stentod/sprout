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

function renderHistory(days) {
  let html = `<h2 style='text-align:center;'>Expenses - Last 7 Days</h2>`;
  if (days.length === 0) {
    html += `<div style='text-align:center; color:#aaa;'>No expenses found.</div>`;
  } else {
    for (const day of days) {
      const dateObj = new Date(day.date);
      const dateStr = dateObj.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
      html += `<div style='margin-top:2rem;'><b>🗓️ ${dateStr}</b><ul style='list-style:none;padding-left:0;'>`;
      for (const exp of day.expenses) {
        html += `<li style='margin:0.5rem 0;'>- $${exp.amount.toFixed(2)}  ${exp.description ? exp.description : ''}</li>`;
      }
      html += `</ul></div>`;
    }
  }
  html += `<div style='text-align:center; margin-top:2rem;'><a href='index.html${window.location.search}' style="background:#333;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px;">Back to Today</a></div>`;
  historyRoot.innerHTML = html;
}

async function loadHistory() {
  try {
    const resp = await fetch(`${API_BASE_URL}/api/history?dayOffset=${dayOffset}`);
    if (!resp.ok) {
      throw new Error(`API returned ${resp.status}`);
    }
    const days = await resp.json();
    renderHistory(days);
  } catch (error) {
    console.warn('API unavailable, showing offline message:', error.message);
    // Try to parse response as JSON to get demo mode info
    let demoMode = false;
    try {
      const errorResponse = await fetch(`${API_BASE_URL}/api/history?dayOffset=${dayOffset}`);
      if (errorResponse.status === 503) {
        const errorJson = await errorResponse.json();
        demoMode = errorJson.demo_mode;
      }
    } catch (e) {
      // Ignore parsing errors
    }
    
    historyRoot.innerHTML = `
      <h2 style='text-align:center;'>Expenses - Last 7 Days</h2>
      <div style='text-align:center; margin:2rem; padding:2rem; background:#333; border-radius:5px; color:#aaa;'>
        <div>⚠️ ${demoMode ? 'Demo mode - Database connection unavailable' : 'Database connection unavailable'}</div>
        <div style='font-size:0.9rem; margin-top:0.5rem;'>History will be available when deployed with a database.</div>
        <div style='margin-top:1rem;'>
          <a href='index.html${window.location.search}' style="background:#555;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px;">Back to Today</a>
        </div>
      </div>
    `;
  }
}

loadHistory(); 