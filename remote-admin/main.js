const state = {
  backend: localStorage.getItem("remoteAdmin.backend") || "",
  token: localStorage.getItem("remoteAdmin.token") || "",
  username: localStorage.getItem("remoteAdmin.username") || "",
};

const loginPanel = document.getElementById("login-panel");
const dashboardPanel = document.getElementById("dashboard-panel");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const whoami = document.getElementById("whoami");
const publicUrl = document.getElementById("public-url");
const servicesNode = document.getElementById("services");
const usersNode = document.getElementById("users");
const createUserForm = document.getElementById("create-user-form");
const newTokenNode = document.getElementById("new-token");

document.getElementById("backend").value = state.backend;
document.getElementById("username").value = state.username;

function normalizedBackend(value) {
  return value.replace(/\/+$/, "");
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }
  const response = await fetch(`${state.backend}${path}`, {
    ...options,
    headers,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    let detail = data.detail || data.message || `Request failed: ${response.status}`;
    if (typeof detail !== "string") {
      detail = Array.isArray(detail)
        ? detail.map((e) => e.msg || JSON.stringify(e)).join("; ")
        : JSON.stringify(detail);
    }
    throw new Error(detail);
  }
  return data;
}

function showLogin(error = "") {
  loginPanel.classList.remove("hidden");
  dashboardPanel.classList.add("hidden");
  loginError.textContent = error;
  loginError.classList.toggle("hidden", !error);
}

function showDashboard() {
  loginPanel.classList.add("hidden");
  dashboardPanel.classList.remove("hidden");
  whoami.textContent = state.username || "Admin";
}

function renderServices(status) {
  publicUrl.textContent = status.public_url ? `Public URL: ${status.public_url}` : "No active public tunnel URL detected.";
  servicesNode.innerHTML = "";
  Object.values(status.services).forEach((service) => {
    const wrapper = document.createElement("article");
    wrapper.className = "service";
    wrapper.innerHTML = `
      <div class="service-header">
        <div>
          <h4>${service.name}</h4>
          <p class="hint">${service.detail || ""}</p>
        </div>
        <span class="badge ${service.running ? "up" : "down"}">${service.running ? "Running" : "Stopped"}</span>
      </div>
      <div class="service-actions">
        <button data-control="start:${service.name}" type="button">Start</button>
        <button data-control="restart:${service.name}" type="button" class="secondary">Restart</button>
        <button data-control="stop:${service.name}" type="button" class="danger">Stop</button>
      </div>
    `;
    servicesNode.appendChild(wrapper);
  });
}

function renderUsers(records) {
  usersNode.innerHTML = "";
  if (!records.length) {
    usersNode.innerHTML = `<p class="hint">No keys yet.</p>`;
    return;
  }
  records.forEach((record) => {
    const wrapper = document.createElement("article");
    wrapper.className = "user";
    wrapper.innerHTML = `
      <form data-key-id="${record.key_id}" class="user-form">
        <div class="service-header">
          <div>
            <h4>${record.key_id}</h4>
            <p class="hint">${record.created}</p>
          </div>
          <span class="chip">${record.department}</span>
        </div>
        <label>Email</label>
        <input name="email" type="email" value="${record.email}" required />
        <label>Department</label>
        <input name="department" value="${record.department}" required />
        <div class="service-actions">
          <button type="submit">Save</button>
          <button type="button" data-rotate="${record.key_id}" class="secondary">Rotate</button>
          <button type="button" data-delete="${record.key_id}" class="danger">Delete</button>
        </div>
      </form>
    `;
    usersNode.appendChild(wrapper);
  });
}

async function refreshDashboard() {
  const [status, users] = await Promise.all([
    api("/admin/api/status"),
    api("/admin/api/users"),
  ]);
  state.username = status.admin.username;
  localStorage.setItem("remoteAdmin.username", state.username);
  showDashboard();
  renderServices(status);
  renderUsers(users.records);
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(loginForm);
  state.backend = normalizedBackend(String(form.get("backend") || ""));
  const username = String(form.get("username") || "");
  const password = String(form.get("password") || "");
  try {
    const login = await fetch(`${state.backend}/admin/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const payload = await login.json().catch(() => ({}));
    if (!login.ok) {
      throw new Error(payload.detail || "Login failed");
    }
    state.token = payload.token;
    state.username = payload.username;
    localStorage.setItem("remoteAdmin.backend", state.backend);
    localStorage.setItem("remoteAdmin.token", state.token);
    localStorage.setItem("remoteAdmin.username", state.username);
    await refreshDashboard();
  } catch (error) {
    showLogin(error.message);
  }
});

document.getElementById("refresh-btn").addEventListener("click", () => refreshDashboard().catch((error) => showLogin(error.message)));
document.getElementById("logout-btn").addEventListener("click", async () => {
  try {
    await api("/admin/api/logout", { method: "POST" });
  } catch (_) {
    // Ignore logout errors while clearing local state.
  }
  state.token = "";
  localStorage.removeItem("remoteAdmin.token");
  showLogin();
});

document.body.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const control = target.getAttribute("data-control");
  if (control) {
    const [action, service] = control.split(":");
    target.setAttribute("disabled", "disabled");
    try {
      await api("/admin/api/control", {
        method: "POST",
        body: JSON.stringify({ action, target: service }),
      });
      await refreshDashboard();
    } catch (error) {
      alert(error.message);
    } finally {
      target.removeAttribute("disabled");
    }
    return;
  }
  const rotateId = target.getAttribute("data-rotate");
  if (rotateId) {
    try {
      const data = await api(`/admin/api/users/${rotateId}/rotate`, { method: "POST" });
      newTokenNode.textContent = data.api_key;
      newTokenNode.classList.remove("hidden");
      await refreshDashboard();
    } catch (error) {
      alert(error.message);
    }
    return;
  }
  const deleteId = target.getAttribute("data-delete");
  if (deleteId) {
    if (!window.confirm(`Delete ${deleteId}?`)) {
      return;
    }
    try {
      await api(`/admin/api/users/${deleteId}`, { method: "DELETE" });
      await refreshDashboard();
    } catch (error) {
      alert(error.message);
    }
  }
});

usersNode.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) {
    return;
  }
  const keyId = form.getAttribute("data-key-id");
  const formData = new FormData(form);
  try {
    await api(`/admin/api/users/${keyId}`, {
      method: "PATCH",
      body: JSON.stringify({
        email: String(formData.get("email") || ""),
        department: String(formData.get("department") || ""),
      }),
    });
    await refreshDashboard();
  } catch (error) {
    alert(error.message);
  }
});

createUserForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(createUserForm);
  try {
    const data = await api("/admin/api/users", {
      method: "POST",
      body: JSON.stringify({
        email: String(formData.get("email") || ""),
        department: String(formData.get("department") || ""),
      }),
    });
    newTokenNode.textContent = data.api_key;
    newTokenNode.classList.remove("hidden");
    createUserForm.reset();
    await refreshDashboard();
  } catch (error) {
    alert(error.message);
  }
});

if (state.backend && state.token) {
  refreshDashboard().catch((error) => showLogin(error.message));
} else {
  showLogin();
}
