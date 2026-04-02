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
  albumSortBy: document.getElementById("albumSortBy"),
  albumSortOrder: document.getElementById("albumSortOrder"),
  searchUsersBtn: document.getElementById("searchUsersBtn"),
  searchAlbumsBtn: document.getElementById("searchAlbumsBtn"),
  statUsers: document.getElementById("statUsers"),
  statAlbums: document.getElementById("statAlbums"),
  statPhotos: document.getElementById("statPhotos"),
  statStorageUsed: document.getElementById("statStorageUsed"),
  usersCountTag: document.getElementById("usersCountTag"),
  albumsCountTag: document.getElementById("albumsCountTag"),
  usersPagination: document.getElementById("usersPagination"),
  albumsPagination: document.getElementById("albumsPagination"),
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
  const t = token();
  return `${API_BASE}/media-proxy?url=${encodeURIComponent(normalized)}${t ? `&token=${encodeURIComponent(t)}` : ""}`;
}

function getAvatarCell(user) {
  const avatar = normalizeMediaUrl(user.avatar_url || "");
  if (!avatar) return `<span class="avatar-fallback">${(user.nickname || user.id || "U").slice(0, 1).toUpperCase()}</span>`;
  const src = mediaProxyUrl(avatar);
  return `<img class="user-avatar" src="${src}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('span'), {className:'avatar-fallback',textContent:'${(user.nickname || user.id || "U").slice(0, 1).toUpperCase()}'}))">`;
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
  // 确保 modal 永远在 body 最末尾，脱离任何父级的 overflow / stacking context 限制
  if (el.modal.parentElement !== document.body) {
    document.body.appendChild(el.modal);
  }
}

function closeModal() {
  el.modal.classList.add("hidden");
}

let state = {
  usersPage: 1,
  usersLimit: 20,
  usersData: [],
  albumsPage: 1,
  albumsLimit: 20,
  albumsData: []
};

function renderPagination(container, current, limit, total, onPageChange) {
  if (!container) return;
  if (total <= 0) {
    container.innerHTML = "";
    return;
  }
  const totalPages = Math.ceil(total / limit);
  const start = (current - 1) * limit + 1;
  const end = Math.min(current * limit, total);
  
  let html = `<div class="page-info">显示 ${start}-${end} 条，共 ${total} 条</div>`;
  
  html += `<button class="page-btn" data-page="${current - 1}" ${current <= 1 ? "disabled" : ""}>上一页</button>`;
  
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= current - 2 && i <= current + 2)) {
      html += `<button class="page-btn ${i === current ? "active" : ""}" data-page="${i}">${i}</button>`;
    } else if (i === current - 3 || i === current + 3) {
      html += `<span class="page-btn" style="border:none;background:transparent;cursor:default;">...</span>`;
    }
  }
  
  html += `<button class="page-btn" data-page="${current + 1}" ${current >= totalPages ? "disabled" : ""}>下一页</button>`;
  
  container.innerHTML = html;
  
  container.querySelectorAll("button.page-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      const targetPage = parseInt(btn.dataset.page, 10);
      if (targetPage && targetPage !== current) {
        onPageChange(targetPage);
      }
    });
  });
}

function setUsersRows(usersData) {
  const users = Array.isArray(usersData) ? usersData : usersData.items || [];
  const total = usersData.total !== undefined ? usersData.total : users.length;
  
  el.usersCountTag.textContent = `${total} 条`;
  if (!users.length) {
    el.usersTbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--muted)">暂无数据</td></tr>`;
    renderPagination(el.usersPagination, state.usersPage, state.usersLimit, 0, null);
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
        <td>
          <button class="btn-primary small quota-btn" data-user-id="${escapeHtml(u.id)}">配额日志</button>
        </td>
      </tr>`
    )
    .join("");
    
  renderPagination(el.usersPagination, state.usersPage, state.usersLimit, total, (page) => {
    state.usersPage = page;
    loadUsers();
  });
}

function setAlbumsRows(albumsData) {
  const albums = Array.isArray(albumsData) ? albumsData : albumsData.items || [];
  const total = albumsData.total !== undefined ? albumsData.total : albums.length;
  
  el.albumsCountTag.textContent = `${total} 条`;
  if (!albums.length) {
    el.albumsTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--muted)">暂无数据</td></tr>`;
    renderPagination(el.albumsPagination, state.albumsPage, state.albumsLimit, 0, null);
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
    
  renderPagination(el.albumsPagination, state.albumsPage, state.albumsLimit, total, (page) => {
    state.albumsPage = page;
    loadAlbums();
  });
}

function setStats(usersData, albumsData) {
  const users = Array.isArray(usersData) ? usersData : usersData.items || [];
  const albums = Array.isArray(albumsData) ? albumsData : albumsData.items || [];
  
  let photoCount = 0;
  let storageUsed = 0;
  for (const u of users) {
    photoCount += Number(u.photo_count || 0);
    storageUsed += Number(u.storage_used || 0);
  }
  
  // 对于分页情况下的总数，我们应当使用接口返回的 total 字段（如果存在）
  const userCount = usersData.total !== undefined ? usersData.total : users.length;
  const albumCount = albumsData.total !== undefined ? albumsData.total : albums.length;
  
  el.statUsers.textContent = fmtInt(userCount);
  el.statAlbums.textContent = fmtInt(albumCount);
  el.statPhotos.textContent = fmtInt(photoCount);
  el.statStorageUsed.textContent = fmtBytes(storageUsed);
}

async function loadUsers() {
  const keyword = el.userKeyword.value.trim();
  const skip = (state.usersPage - 1) * state.usersLimit;
  const query = new URLSearchParams({ skip, limit: state.usersLimit });
  if (keyword) query.set("keyword", keyword);
  
  el.usersTbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--muted)">加载中...</td></tr>`;
  try {
    const users = await request(`/users?${query.toString()}`);
    setUsersRows(users);
    return users;
  } catch (err) {
    el.usersTbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--danger)">加载失败: ${escapeHtml(err.message)}</td></tr>`;
    return [];
  }
}

async function loadAlbums() {
  const keyword = el.albumKeyword.value.trim();
  const sortBy = el.albumSortBy ? el.albumSortBy.value : "created_at";
  const order = el.albumSortOrder ? el.albumSortOrder.value : "desc";
  const skip = (state.albumsPage - 1) * state.albumsLimit;
  const query = new URLSearchParams({ skip, limit: state.albumsLimit, sort_by: sortBy, order: order });
  if (keyword) query.set("keyword", keyword);
  
  el.albumsTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--muted)">加载中...</td></tr>`;
  try {
    const albums = await request(`/albums?${query.toString()}`);
    setAlbumsRows(albums);
    return albums;
  } catch (err) {
    el.albumsTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--danger)">加载失败: ${escapeHtml(err.message)}</td></tr>`;
    return [];
  }
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
    <div class="photo-grid">
      ${
        photos.length
          ? photos
              .map((p) => {
                const thumb = p.thumbnail_url || p.url || "";
                const thumbProxy = mediaProxyUrl(thumb);
                const rawLink = normalizeMediaUrl(p.url || "");
                const link = rawLink ? `href="${escapeHtml(rawLink)}"` : "";
                const ownerAvatar = normalizeMediaUrl(p.owner_avatar_url || "");
                const ownerAvatarProxy = mediaProxyUrl(ownerAvatar);
                const ownerName = p.owner_nickname || p.owner_id || "未知用户";
                const ownerInitial = (ownerName || "U").slice(0, 1).toUpperCase();
                const ownerAvatarHtml = ownerAvatarProxy
                  ? `<img class="photo-owner-avatar" src="${ownerAvatarProxy}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('span'), {className:'photo-owner-avatar-fallback',textContent:'${escapeHtml(ownerInitial)}'}))">`
                  : `<span class="photo-owner-avatar-fallback">${escapeHtml(ownerInitial)}</span>`;
                const img = thumbProxy ? `<img class="photo-card-img" src="${thumbProxy}" alt="" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 100 100\\'><rect width=\\'100\\' height=\\'100\\' fill=\\'%23edf3ff\\'/><text x=\\'50\\' y=\\'50\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\' fill=\\'%238593af\\' font-size=\\'14\\'>无图</text></svg>'">` : `<div class="photo-card-img-placeholder">无图</div>`;
                return `
                  <a class="photo-card" ${link} target="_blank" rel="noopener noreferrer">
                    <div class="photo-card-img-wrapper">${img}</div>
                    <div class="photo-card-info">
                      <div class="photo-owner-row">
                        ${ownerAvatarHtml}
                        <span class="photo-owner-name">${escapeHtml(ownerName)}</span>
                      </div>
                      <div class="photo-card-time">${fmtTime(p.created_at)}</div>
                      <div class="photo-card-size">${fmtBytes(p.size)}</div>
                    </div>
                  </a>
                `;
              })
              .join("")
          : `<div class="photo-grid-empty">该相册暂无照片</div>`
      }
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
  el.searchUsersBtn.addEventListener("click", () => {
    state.usersPage = 1;
    loadUsers();
  });
  el.searchAlbumsBtn.addEventListener("click", () => {
    state.albumsPage = 1;
    loadAlbums();
  });
  el.closeModalBtn.addEventListener("click", closeModal);
  el.modal.addEventListener("click", (e) => {
    if (e.target === el.modal) closeModal();
  });
  for (const tab of el.tabs) {
    tab.addEventListener("click", () => setTab(tab.dataset.tab));
  }

  // 修复：事件委托绑定在正确的 DOM 元素上，这里原本可能是绑在 el.usersTbody/albumsTbody 上，
  // 但我们每次渲染时重写了 innerHTML，必须确保绑定在父容器或直接绑在不被替换的 DOM 上，或者使用全局代理
  document.body.addEventListener("click", (e) => {
    const quotaBtn = e.target.closest(".quota-btn");
    if (quotaBtn) {
      showUserQuotaLogs(quotaBtn.dataset.userId);
      return;
    }
    const photosBtn = e.target.closest(".photos-btn");
    if (photosBtn) {
      showAlbumPhotos(photosBtn.dataset.albumId, photosBtn.dataset.albumName);
      return;
    }
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
