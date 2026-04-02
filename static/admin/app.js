const API_BASE = "/cs-server/admin-api";
const TOKEN_KEY = "camera_admin_token";

const el = {
  loginView: document.getElementById("loginView"),
  appView: document.getElementById("appView"),
  loginForm: document.getElementById("loginForm"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  loginError: document.getElementById("loginError"),
  logoutBtn: document.getElementById("logoutBtn"),
  tabs: Array.from(document.querySelectorAll(".tab")),
  usersPanel: document.getElementById("usersPanel"),
  albumsPanel: document.getElementById("albumsPanel"),
  usersTbody: document.getElementById("usersTbody"),
  albumsTbody: document.getElementById("albumsTbody"),
  userKeyword: document.getElementById("userKeyword"),
  albumKeyword: document.getElementById("albumKeyword"),
  searchUsersBtn: document.getElementById("searchUsersBtn"),
  searchAlbumsBtn: document.getElementById("searchAlbumsBtn"),
  statUsers: document.getElementById("statUsers"),
  statAlbums: document.getElementById("statAlbums"),
  statPhotos: document.getElementById("statPhotos"),
  statStorageUsed: document.getElementById("statStorageUsed"),
  usersCountTag: document.getElementById("usersCountTag"),
  albumsCountTag: document.getElementById("albumsCountTag"),
  modal: document.getElementById("modal"),
  modalTitle: document.getElementById("modalTitle"),
  modalBody: document.getElementById("modalBody"),
  closeModalBtn: document.getElementById("closeModalBtn"),
};

function token() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(value) {
  if (value) {
    localStorage.setItem(TOKEN_KEY, value);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function fmtTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("zh-CN", { hour12: false });
}

function fmtBytes(bytes) {
  const n = Number(bytes || 0);
  if (!n) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = n;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 2)} ${units[idx]}`;
}

function fmtInt(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return map[char] || char;
  });
}

function normalizeMediaUrl(rawUrl) {
  if (!rawUrl) return "";
  const url = String(rawUrl).trim();
  if (!url) return "";
  if (url.startsWith("//")) {
    return `${window.location.protocol}${url}`;
  }
  if (url.startsWith("/")) {
    return `${window.location.origin}${url}`;
  }
  try {
    const parsed = new URL(url);
    if (window.location.protocol === "https:" && parsed.protocol === "http:") {
      parsed.protocol = "https:";
      return parsed.toString();
    }
    return parsed.toString();
  } catch (_) {
    return url;
  }
}

function mediaProxyUrl(rawUrl) {
  const normalized = normalizeMediaUrl(rawUrl);
  if (!normalized) return "";
  return `${API_BASE}/media-proxy?url=${encodeURIComponent(normalized)}`;
}

function getAvatarCell(user) {
  const avatar = normalizeMediaUrl(user.avatar_url || "");
  if (!avatar) return `<span class="avatar-fallback">${(user.nickname || "U").slice(0, 1).toUpperCase()}</span>`;
  const src = mediaProxyUrl(avatar);
  return `<img class="user-avatar" src="${src}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('span'), {className:'avatar-fallback',textContent:'U'}))">`;
}

async function request(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
  };
  if (token()) headers.Authorization = `Bearer ${token()}`;
  if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (res.status === 401) {
    setToken("");
    showLogin();
    throw new Error("认证失效，请重新登录");
  }
  if (!res.ok) {
    let msg = `请求失败 (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) msg = data.detail;
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

function showLogin() {
  el.loginView.classList.remove("hidden");
  el.appView.classList.add("hidden");
}

function showApp() {
  el.loginView.classList.add("hidden");
  el.appView.classList.remove("hidden");
}

function setTab(name) {
  el.tabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === name);
  });
  el.usersPanel.classList.toggle("hidden", name !== "users");
  el.albumsPanel.classList.toggle("hidden", name !== "albums");
  
  // 更新页面标题
  if (name === "users") {
    document.getElementById("pageTitle").textContent = "用户管理";
  } else if (name === "albums") {
    document.getElementById("pageTitle").textContent = "相册管理";
  }
}

function openModal(title, html) {
  el.modalTitle.textContent = title;
  el.modalBody.innerHTML = html;
  el.modal.classList.remove("hidden");
  document.body.appendChild(el.modal);
}

function closeModal() {
  el.modal.classList.add("hidden");
}

function setUsersRows(users) {
  el.usersCountTag.textContent = `${users.length} 条`;
  if (!users.length) {
    el.usersTbody.innerHTML = `<tr><td colspan="9">暂无数据</td></tr>`;
    return;
  }
  el.usersTbody.innerHTML = users
    .map(
      (u) => `<tr>
        <td>${getAvatarCell(u)}</td>
        <td>${escapeHtml(u.id || "-")}</td>
        <td>${escapeHtml(u.nickname || "-")}</td>
        <td>${escapeHtml(u.email || "-")}</td>
        <td>${fmtTime(u.last_login_at)}</td>
        <td>${fmtInt(u.album_count)}</td>
        <td>${fmtInt(u.photo_count)}</td>
        <td>${fmtBytes(u.storage_used)}</td>
        <td>${fmtBytes(u.storage_limit)}</td>
        <td><button class="small ghost quota-btn" data-user-id="${escapeHtml(u.id)}">配额日志</button></td>
      </tr>`
    )
    .join("");
}

function setAlbumsRows(albums) {
  el.albumsCountTag.textContent = `${albums.length} 条`;
  if (!albums.length) {
    el.albumsTbody.innerHTML = `<tr><td colspan="7">暂无数据</td></tr>`;
    return;
  }
  el.albumsTbody.innerHTML = albums
    .map(
      (a) => `<tr>
        <td>${escapeHtml(a.id)}</td>
        <td>${escapeHtml(a.name || "-")}</td>
        <td>${a.owner_nickname ? escapeHtml(a.owner_nickname) : escapeHtml(a.owner_id || "-")}</td>
        <td><span class="badge ${a.is_default ? "badge-primary" : "badge-neutral"}">${a.is_default ? "默认" : "普通"}</span></td>
        <td>${fmtInt(a.photo_count)}</td>
        <td>${fmtTime(a.created_at)}</td>
        <td><button class="small ghost photos-btn" data-album-id="${escapeHtml(a.id)}" data-album-name="${escapeHtml(a.name || "")}">查看照片</button></td>
      </tr>`
    )
    .join("");
}

function setStats(users, albums) {
  const userCount = users.length;
  const albumCount = albums.length;
  let photoCount = 0;
  let storageUsed = 0;
  for (const u of users) {
    photoCount += Number(u.photo_count || 0);
    storageUsed += Number(u.storage_used || 0);
  }
  el.statUsers.textContent = fmtInt(userCount);
  el.statAlbums.textContent = fmtInt(albumCount);
  el.statPhotos.textContent = fmtInt(photoCount);
  el.statStorageUsed.textContent = fmtBytes(storageUsed);
}

async function loadUsers() {
  const keyword = el.userKeyword.value.trim();
  const data = await request(`/users${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`);
  setUsersRows(data);
  return data;
}

async function loadAlbums() {
  const keyword = el.albumKeyword.value.trim();
  const data = await request(`/albums${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`);
  setAlbumsRows(data);
  return data;
}

async function refreshDashboard() {
  const [users, albums] = await Promise.all([loadUsers(), loadAlbums()]);
  setStats(users, albums);
}

async function showUserQuotaLogs(userId) {
  const logs = await request(`/users/${encodeURIComponent(userId)}/quota-logs`);
  const html = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>变化量</th>
            <th>当前限额</th>
            <th>原因</th>
            <th>引用ID</th>
            <th>操作人</th>
          </tr>
        </thead>
        <tbody>
          ${
            logs.length
              ? logs
                  .map(
                    (l) => `<tr>
                      <td>${fmtTime(l.created_at)}</td>
                      <td>${fmtBytes(l.change_amount)}</td>
                      <td>${fmtBytes(l.current_limit)}</td>
                      <td>${l.reason || "-"}</td>
                      <td>${l.reference_id || "-"}</td>
                      <td>${l.operator || "-"}</td>
                    </tr>`
                  )
                  .join("")
              : `<tr><td colspan="6">暂无日志</td></tr>`
          }
        </tbody>
      </table>
    </div>
  `;
  openModal(`用户配额日志 · ${userId}`, html);
}

async function showAlbumPhotos(albumId, albumName) {
  const photos = await request(`/albums/${encodeURIComponent(albumId)}/photos`);
  const html = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>缩略图</th>
            <th>文件名</th>
            <th>大小</th>
            <th>上传者</th>
            <th>创建时间</th>
            <th>链接</th>
          </tr>
        </thead>
        <tbody>
          ${
            photos.length
              ? photos
                  .map((p) => {
                    const thumb = p.thumbnail_url || p.url || "";
                    const thumbProxy = mediaProxyUrl(thumb);
                    const rawLink = normalizeMediaUrl(p.url || "");
                    const link = rawLink ? `<a href="${escapeHtml(rawLink)}" target="_blank" rel="noopener noreferrer">查看原图</a>` : "-";
                    const img = thumbProxy ? `<img class="photo-thumb" src="${thumbProxy}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('span'), {className:'avatar-fallback',textContent:'无图'}))">` : "-";
                    return `<tr>
                      <td>${img}</td>
                      <td>${escapeHtml(p.filename || "-")}</td>
                      <td>${fmtBytes(p.size)}</td>
                      <td>${escapeHtml(p.owner_id || "-")}</td>
                      <td>${fmtTime(p.created_at)}</td>
                      <td>${link}</td>
                    </tr>`;
                  })
                  .join("")
              : `<tr><td colspan="6">该相册暂无照片</td></tr>`
          }
        </tbody>
      </table>
    </div>
  `;
  openModal(`相册照片 · ${albumName || albumId}`, html);
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  el.loginError.textContent = "";
  try {
    const data = await request("/login", {
      method: "POST",
      body: { username: el.username.value.trim(), password: el.password.value },
    });
    setToken(data.access_token);
    showApp();
    await refreshDashboard();
  } catch (err) {
    el.loginError.textContent = err.message || "登录失败";
  }
}

function bindEvents() {
  el.loginForm.addEventListener("submit", handleLoginSubmit);
  el.logoutBtn.addEventListener("click", () => {
    setToken("");
    showLogin();
  });
  el.searchUsersBtn.addEventListener("click", loadUsers);
  el.searchAlbumsBtn.addEventListener("click", loadAlbums);
  el.closeModalBtn.addEventListener("click", closeModal);
  el.modal.addEventListener("click", (e) => {
    if (e.target === el.modal) closeModal();
  });
  for (const tab of el.tabs) {
    tab.addEventListener("click", () => setTab(tab.dataset.tab));
  }
  el.usersTbody.addEventListener("click", (e) => {
    const btn = e.target.closest(".quota-btn");
    if (!btn) return;
    showUserQuotaLogs(btn.dataset.userId);
  });
  el.albumsTbody.addEventListener("click", (e) => {
    const btn = e.target.closest(".photos-btn");
    if (!btn) return;
    showAlbumPhotos(btn.dataset.albumId, btn.dataset.albumName);
  });
}

async function bootstrap() {
  bindEvents();
  if (!token()) {
    showLogin();
    return;
  }
  try {
    showApp();
    await refreshDashboard();
  } catch (_) {
    showLogin();
  }
}

bootstrap();
