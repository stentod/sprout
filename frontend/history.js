// Utility: Get dayOffset from query string
function getDayOffset() {
  const params = new URLSearchParams(window.location.search);
  return parseInt(params.get('dayOffset') || '0', 10);
}

const dayOffset = getDayOffset();
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
  const resp = await fetch(`http://localhost:5000/api/history?dayOffset=${dayOffset}`);
  const days = await resp.json();
  renderHistory(days);
}

loadHistory(); 