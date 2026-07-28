const API = "/api";
let state = {
  tab: "dashboard",
  employees: [],
  leaveRequests: [],
  teams: [],
  employeeFilter: "",
  employeeSort: { key: null, dir: 1 },
  leaveFilter: "",
  leaveStatusFilter: "all",
  leaveSort: { key: null, dir: 1 },
  payrollRuns: [],
  currentPayrollView: null,
};

// Safe string escaping function to prevent XSS
function escapeHTML(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function api(path, opts) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.error || "Request failed");
  }
  return res.json();
}

async function loadCommon() {
  state.employees = await api("/employees");
  state.leaveRequests = await api("/leave");
  state.teams = await api("/employees/teams");
}

function renderNav() {
  document.querySelectorAll("nav button").forEach(b => {
    b.classList.toggle("active", b.dataset.tab === state.tab);
  });
}

function flaggedCount() {
  return state.leaveRequests.filter(r => r.status === "pending" && r.flags.length > 0).length;
}

function renderNotificationBanner() {
  const count = flaggedCount();
  if (count === 0) return "";
  return `<div class="banner">${count} entr${count > 1 ? "ies" : "y"} in the pending ledger carry a flag — notice, coverage, balance, or age.</div>`;
}

/* ---------- Generic Sort Helpers ---------- */
function sortRows(rows, sortState, accessor) {
  if (!sortState.key) return rows;
  return [...rows].sort((a, b) => {
    const av = accessor(a, sortState.key);
    const bv = accessor(b, sortState.key);
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * sortState.dir;
    return String(av).localeCompare(String(bv)) * sortState.dir;
  });
}

function toggleSort(sortState, key) {
  if (sortState.key === key) sortState.dir *= -1;
  else { sortState.key = key; sortState.dir = 1; }
}

/* ---------- Dashboard ---------- */
async function renderDashboard() {
  const pending = state.leaveRequests.filter(r => r.status === "pending");
  const whoIsOut = await api("/leave/who-is-out");
  const balances = await api("/leave/balances");

  let html = renderNotificationBanner();

  html += `<div class="card"><h2>Pending Approvals (${pending.length})</h2>`;
  html += pending.length ? renderLeaveTable(pending, true) : `<div class="empty">Ledger clear — nothing awaiting a decision.</div>`;
  html += `</div>`;

  html += `<div class="card"><h2>Who's Out Today (${whoIsOut.length})</h2>`;
  html += whoIsOut.length
    ? `<table><tr><th>Employee</th><th>Dates</th></tr>` +
      whoIsOut.map(r => `<tr><td>${escapeHTML(r.employee_name)}</td><td>${escapeHTML(r.start_date)} → ${escapeHTML(r.end_date)}</td></tr>`).join("") +
      `</table>`
    : `<div class="empty">Ledger clear — nobody's out today.</div>`;
  html += `</div>`;

  html += `<div class="card"><h2>Leave Balances (${new Date().getFullYear()})</h2>`;
  html += balances.length
    ? `<table><tr><th>Employee</th><th class="num">Allocated</th><th class="num">Used</th><th class="num">Remaining</th></tr>` +
      balances.map(b => `
        <tr>
          <td>${escapeHTML(b.employee_name)}</td><td class="num">${b.allocated_days}</td><td class="num">${b.used_days}</td>
          <td class="num ${b.remaining_days <= 0 ? 'balance-low' : 'balance-ok'}">${b.remaining_days}</td>
        </tr>`).join("") + `</table>`
    : `<div class="empty">No entries yet.</div>`;
  html += `</div>`;

  return html;
}

/* ---------- Leave Table Component ---------- */
function renderLeaveTable(requests, showActions) {
  const header = `<tr>
    <th class="sortable" data-sort-leave="employee_name">Employee</th>
    <th>Dates</th>
    <th class="num sortable" data-sort-leave="days_requested">Days</th>
    <th class="sortable" data-sort-leave="status">Status</th>
    <th>Flags</th>${showActions ? "<th></th>" : ""}</tr>`;

  return `<table>${header}` +
    requests.map(r => {
      const canApprove = r.status === "pending" || r.status === "rejected";
      const canReject = r.status === "pending" || r.status === "approved";
      const canWithdraw = r.status === "pending" || r.status === "approved";
      return `
      <tr data-id="${r.id}">
        <td>${escapeHTML(r.employee_name)}</td>
        <td>${escapeHTML(r.start_date)} → ${escapeHTML(r.end_date)}</td>
        <td class="num">${r.days_requested}${r.is_unpaid ? ` (unpaid: ${r.unpaid_days})` : ""}</td>
        <td class="status-${r.status}">${escapeHTML(r.status)}</td>
        <td>${r.flags.map(f => `<span class="flag">${escapeHTML(f.replace(/_/g, " "))}</span>`).join("")}</td>
        ${showActions ? `<td class="actions-cell">
          ${canApprove ? `<button class="action approve" data-action="approve" data-id="${r.id}">Approve</button>` : ""}
          ${canReject ? `<button class="action reject" data-action="reject" data-id="${r.id}">Reject</button>` : ""}
          ${canWithdraw ? `<button class="action withdraw" data-action="withdraw" data-id="${r.id}">Withdraw</button>` : ""}
        </td>` : ""}
      </tr>`;
    }).join("") + `</table>`;
}

const CONFIRM_MESSAGES = {
  approve: "Approve this leave request?",
  reject: "Reject this leave request? Any balance already consumed will be returned.",
  withdraw: "Withdraw this leave request? Any balance already consumed will be returned.",
};

async function decideLeave(id, action) {
  if (!confirm(CONFIRM_MESSAGES[action])) return;
  try {
    await api(`/leave/${id}/${action}`, { method: "POST", body: JSON.stringify({ decided_by: "Manager" }) });
    const cell = document.querySelector(`tr[data-id="${id}"] .actions-cell`);
    if (cell && (action === "approve" || action === "reject")) {
      const stamp = document.createElement("div");
      stamp.className = `stamp stamp-${action}`;
      stamp.textContent = action === "approve" ? "APPROVED" : "REJECTED";
      cell.appendChild(stamp);
      setTimeout(async () => { await loadCommon(); render(); }, 600);
    } else {
      await loadCommon();
      render();
    }
  } catch (err) {
    alert(err.message);
  }
}

/* ---------- Employees Tab ---------- */
function filteredSortedEmployees() {
  let rows = state.employees.filter(e => e.name.toLowerCase().includes(state.employeeFilter.toLowerCase()));
  rows = sortRows(rows, state.employeeSort, (row, key) => key === "salary" ? row.salary : (row[key] || ""));
  return rows;
}

function employeeCountLabel() {
  const rows = filteredSortedEmployees();
  return `Employees (${rows.length}${rows.length !== state.employees.length ? ` of ${state.employees.length}` : ""})`;
}

function employeeTableHTML() {
  const rows = filteredSortedEmployees();
  if (!rows.length) return `<div class="empty">No entries match.</div>`;
  return `<table><tr>
      <th class="sortable" data-sort-emp="name">Name</th>
      <th class="sortable" data-sort-emp="role">Role</th>
      <th class="sortable" data-sort-emp="team_name">Team</th>
      <th>Manager</th>
      <th class="sortable" data-sort-emp="start_date">Start</th>
      <th class="num sortable" data-sort-emp="salary">Salary</th>
      <th></th>
    </tr>` +
    rows.map(e => `
      <tr>
        <td>${escapeHTML(e.name)}</td><td>${escapeHTML(e.role)}</td><td>${escapeHTML(e.team_name || "—")}</td>
        <td>${escapeHTML(e.manager_name || "—")}</td><td>${escapeHTML(e.start_date)}</td><td class="num">${e.salary.toLocaleString()}</td>
        <td><button class="action reject" data-action="deactivate-emp" data-id="${e.id}">Deactivate</button></td>
      </tr>`).join("") + `</table>`;
}

function refreshEmployeeTable() {
  const container = document.getElementById("employee-table-container");
  if (container) container.innerHTML = employeeTableHTML();
  const label = document.getElementById("employee-count-label");
  if (label) label.textContent = employeeCountLabel();
}

function renderEmployees() {
  let html = `<div class="card"><h2>Add Team</h2>
    <form class="inline" id="form-add-team">
      <input name="team_name" placeholder="Team name" required>
      <button class="action approve" type="submit">Add Team</button>
    </form></div>`;

  html += `<div class="card"><h2>Add Employee</h2>
    <form class="inline" id="form-add-employee">
      <input name="name" placeholder="Name" required>
      <input name="role" placeholder="Role" required>
      <select name="team_id">
        <option value="">No team</option>
        ${state.teams.map(t => `<option value="${t.id}">${escapeHTML(t.name)}</option>`).join("")}
      </select>
      <select name="manager_id">
        <option value="">No manager</option>
        ${state.employees.map(e => `<option value="${e.id}">${escapeHTML(e.name)}</option>`).join("")}
      </select>
      <input name="start_date" type="date" required>
      <input name="salary" type="number" placeholder="Monthly salary" required>
      <select name="employment_type">
        <option value="full_time">Full time</option>
        <option value="contract">Contract</option>
        <option value="part_time">Part time</option>
      </select>
      <button class="action approve" type="submit">Add</button>
    </form></div>`;

  html += `<div class="card"><h2 id="employee-count-label">${employeeCountLabel()}</h2>
    <form class="inline" onsubmit="return false">
      <input id="employee-search-input" placeholder="Search by name..." value="${escapeHTML(state.employeeFilter)}">
    </form>
    <div id="employee-table-container">${employeeTableHTML()}</div>
  </div>`;
  return html;
}

async function deactivateEmployee(id) {
  if (!confirm("Deactivate this employee? Their records are kept, but they'll be hidden from active lists and future payroll.")) return;
  await api(`/employees/${id}/deactivate`, { method: "POST" });
  await loadCommon();
  render();
}

/* ---------- Leave Tab ---------- */
function filteredSortedLeave() {
  let rows = state.leaveRequests.filter(r => {
    const matchesName = r.employee_name.toLowerCase().includes(state.leaveFilter.toLowerCase());
    const matchesStatus = state.leaveStatusFilter === "all" || r.status === state.leaveStatusFilter;
    return matchesName && matchesStatus;
  });
  rows = sortRows(rows, state.leaveSort, (row, key) => row[key]);
  return rows;
}

function leaveCountLabel() {
  const rows = filteredSortedLeave();
  return `All Leave Requests (${rows.length}${rows.length !== state.leaveRequests.length ? ` of ${state.leaveRequests.length}` : ""})`;
}

function leaveTableHTML() {
  const rows = filteredSortedLeave();
  if (!rows.length) return `<div class="empty">No entries match.</div>`;
  return renderLeaveTable(rows, true);
}

function refreshLeaveTable() {
  const container = document.getElementById("leave-table-container");
  if (container) container.innerHTML = leaveTableHTML();
  const label = document.getElementById("leave-count-label");
  if (label) label.textContent = leaveCountLabel();
}

function renderLeave() {
  let html = `<div class="card"><h2>Submit Leave Request</h2>
    <form class="inline" id="form-submit-leave">
      <select name="employee_id" required>
        <option value="">Select employee</option>
        ${state.employees.map(e => `<option value="${e.id}">${escapeHTML(e.name)}</option>`).join("")}
      </select>
      <input name="start_date" type="date" required>
      <input name="end_date" type="date" required>
      <input name="reason" placeholder="Reason (optional)">
      <button class="action approve" type="submit">Submit</button>
    </form></div>`;

  html += `<div class="card"><h2 id="leave-count-label">${leaveCountLabel()}</h2>
    <form class="inline" onsubmit="return false">
      <input id="leave-search-input" placeholder="Search by employee..." value="${escapeHTML(state.leaveFilter)}">
      <select id="leave-status-select">
        <option value="all" ${state.leaveStatusFilter === 'all' ? 'selected' : ''}>All statuses</option>
        <option value="pending" ${state.leaveStatusFilter === 'pending' ? 'selected' : ''}>Pending</option>
        <option value="approved" ${state.leaveStatusFilter === 'approved' ? 'selected' : ''}>Approved</option>
        <option value="rejected" ${state.leaveStatusFilter === 'rejected' ? 'selected' : ''}>Rejected</option>
        <option value="withdrawn" ${state.leaveStatusFilter === 'withdrawn' ? 'selected' : ''}>Withdrawn</option>
      </select>
    </form>
    <div id="leave-table-container">${leaveTableHTML()}</div>
  </div>`;
  return html;
}

/* ---------- Payroll Tab ---------- */
async function renderPayroll() {
  const now = new Date();
  state.payrollRuns = await api("/payroll");

  let html = `<div class="card"><h2>Generate Payroll</h2>
    <form class="inline" id="form-generate-payroll">
      <select name="month">${Array.from({length:12},(_,i)=>`<option value="${i+1}" ${i+1===now.getMonth()+1?"selected":""}>${i+1}</option>`).join("")}</select>
      <input name="year" type="number" value="${now.getFullYear()}" style="width:90px">
      <button class="action approve" type="submit">Generate</button>
    </form>
  </div>`;

  html += `<div class="card"><h2>Past Payroll Runs (${state.payrollRuns.length})</h2>`;
  html += state.payrollRuns.length
    ? `<table><tr><th>Period</th><th class="num">Employees Paid</th><th>Generated</th><th></th></tr>` +
      state.payrollRuns.map(r => `
        <tr>
          <td>${r.period_year}-${String(r.period_month).padStart(2, "0")}</td>
          <td class="num">${r.employee_count}</td>
          <td>${new Date(r.generated_at).toLocaleString()}</td>
          <td><button class="action approve" data-action="view-payroll" data-year="${r.period_year}" data-month="${r.period_month}">View</button></td>
        </tr>`).join("") + `</table>`
    : `<div class="empty">No payroll has been generated yet.</div>`;
  html += `</div>`;

  html += `<div id="payroll-result">${state.currentPayrollView ? renderPayslips(state.currentPayrollView.payslips, state.currentPayrollView.year, state.currentPayrollView.month) : ""}</div>`;

  return html;
}

function renderPayslips(payslips, year, month) {
  if (!payslips.length) return `<div class="empty">No active employees to pay for this period.</div>`;
  let html = `<div class="card"><h2>Payslips — ${year}-${String(month).padStart(2, "0")}</h2>`;
  html += `<table><tr><th>Employee</th><th class="num">Working Days</th><th class="num">Unpaid Days</th><th class="num">Gross</th><th class="num">Tax</th><th class="num">Social Security</th><th class="num">Net</th></tr>` +
    payslips.map(p => `
      <tr>
        <td>${escapeHTML(p.employee_name)}</td><td class="num">${p.working_days}</td><td class="num">${p.unpaid_leave_days}</td>
        <td class="num">${p.gross_pay.toLocaleString()}</td><td class="num">${p.tax_deducted.toLocaleString()}</td>
        <td class="num">${p.social_security_deducted.toLocaleString()}</td><td class="num"><strong>${p.net_pay.toLocaleString()}</strong></td>
      </tr>`).join("") + `</table>`;
  html += `<a class="export-link" href="${API}/payroll/${year}/${month}/export" target="_blank">Export CSV</a>`;
  html += `</div>`;
  return html;
}

/* ---------- Global Router & Event Delegation ---------- */
async function render() {
  renderNav();
  const app = document.getElementById("app");
  app.innerHTML = `<div class="loading">Loading...</div>`;
  let html = "";
  if (state.tab === "dashboard") html = await renderDashboard();
  else if (state.tab === "employees") html = renderEmployees();
  else if (state.tab === "leave") html = renderLeave();
  else if (state.tab === "payroll") html = await renderPayroll();
  app.innerHTML = html;
}

// Global Event Listener (Centralized Event Handling)
document.addEventListener("click", async (e) => {
  const target = e.target;

  // Navigation
  if (target.closest("nav button")) {
    state.tab = target.closest("nav button").dataset.tab;
    await render();
    return;
  }

  // Table Sorting
  if (target.dataset.sortEmp) {
    toggleSort(state.employeeSort, target.dataset.sortEmp);
    refreshEmployeeTable();
    return;
  }
  if (target.dataset.sortLeave) {
    toggleSort(state.leaveSort, target.dataset.sortLeave);
    refreshLeaveTable();
    return;
  }

  // Leave Actions (Approve, Reject, Withdraw)
  if (target.dataset.action && ["approve", "reject", "withdraw"].includes(target.dataset.action)) {
    decideLeave(parseInt(target.dataset.id), target.dataset.action);
    return;
  }

  // Deactivate Employee
  if (target.dataset.action === "deactivate-emp") {
    deactivateEmployee(parseInt(target.dataset.id));
    return;
  }

  // View Past Payroll
  if (target.dataset.action === "view-payroll") {
    const year = parseInt(target.dataset.year);
    const month = parseInt(target.dataset.month);
    const data = await api(`/payroll/${year}/${month}`);
    state.currentPayrollView = { year, month, payslips: data.payslips || [] };
    render();
    return;
  }
});

// Input & Form Event Handlers
document.addEventListener("input", (e) => {
  if (e.target.id === "employee-search-input") {
    state.employeeFilter = e.target.value;
    refreshEmployeeTable();
  }
  if (e.target.id === "leave-search-input") {
    state.leaveFilter = e.target.value;
    refreshLeaveTable();
  }
});

document.addEventListener("change", (e) => {
  if (e.target.id === "leave-status-select") {
    state.leaveStatusFilter = e.target.value;
    refreshLeaveTable();
  }
});

document.addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;

  if (f.id === "form-add-team") {
    await api("/employees/teams", { method: "POST", body: JSON.stringify({ name: f.team_name.value }) });
    state.teams = await api("/employees/teams");
    render();
  }

  if (f.id === "form-add-employee") {
    await api("/employees", {
      method: "POST",
      body: JSON.stringify({
        name: f.name.value,
        role: f.role.value,
        team_id: f.team_id.value ? parseInt(f.team_id.value) : null,
        manager_id: f.manager_id.value ? parseInt(f.manager_id.value) : null,
        start_date: f.start_date.value,
        salary: parseFloat(f.salary.value),
        employment_type: f.employment_type.value,
      }),
    });
    await loadCommon();
    render();
  }

  if (f.id === "form-submit-leave") {
    try {
      await api("/leave", {
        method: "POST",
        body: JSON.stringify({
          employee_id: parseInt(f.employee_id.value),
          start_date: f.start_date.value,
          end_date: f.end_date.value,
          reason: f.reason.value,
        }),
      });
    } catch (err) { alert(err.message); }
    await loadCommon();
    render();
  }

  if (f.id === "form-generate-payroll") {
    const month = parseInt(f.month.value);
    const year = parseInt(f.year.value);
    try {
      const data = await api("/payroll/generate", { method: "POST", body: JSON.stringify({ month, year }) });
      state.currentPayrollView = { year, month, payslips: data.payslips };
    } catch (err) {
      state.currentPayrollView = null;
      alert(err.message);
    }
    render();
  }
});

// App Initialization
(async () => {
  await loadCommon();
  await render();
})();