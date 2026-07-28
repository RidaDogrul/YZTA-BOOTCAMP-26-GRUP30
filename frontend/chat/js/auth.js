/**
 * auth.js — Login/Register modal mantığı ve auth UI güncellemeleri
 *
 * api.js'e bağımlıdır:
 *   apiLogin, apiRegister, apiLogout, getAuthToken, getAuthUser,
 *   setAuthToken, setAuthUser, isAuthenticated
 */

/* ─── DOM Referansları ────────────────────────────────────── */
const authModal        = document.getElementById("authModal");
const panelLogin       = document.getElementById("panelLogin");
const panelRegister    = document.getElementById("panelRegister");
const tabLogin         = document.getElementById("tabLogin");
const tabRegister      = document.getElementById("tabRegister");
const loginForm        = document.getElementById("loginForm");
const registerForm     = document.getElementById("registerForm");
const loginError       = document.getElementById("loginError");
const registerError    = document.getElementById("registerError");
const btnLoginSubmit   = document.getElementById("btnLoginSubmit");
const btnRegisterSubmit = document.getElementById("btnRegisterSubmit");
const btnLogin         = document.getElementById("btnLogin");
const btnLogout        = document.getElementById("btnLogout");
const authUserChip     = document.getElementById("authUserChip");
const authUsername     = document.getElementById("authUsername");
const authAvatar       = document.getElementById("authAvatar");

/* ─── Modal Aç/Kapat ──────────────────────────────────────── */

function openAuthModal(tab = "login") {
  authModal.style.display = "flex";
  document.body.style.overflow = "hidden";
  switchAuthTab(tab);
  // İlk input'a odaklan
  requestAnimationFrame(() => {
    const first = authModal.querySelector(".auth-input");
    if (first) first.focus();
  });
}

function closeAuthModal() {
  authModal.style.display = "none";
  document.body.style.overflow = "";
  clearAuthErrors();
  loginForm.reset();
  registerForm.reset();
}

/* ─── Tab Geçişi ──────────────────────────────────────────── */

function switchAuthTab(tab) {
  const isLogin = tab === "login";

  tabLogin.classList.toggle("active", isLogin);
  tabLogin.setAttribute("aria-selected", String(isLogin));
  tabRegister.classList.toggle("active", !isLogin);
  tabRegister.setAttribute("aria-selected", String(!isLogin));

  panelLogin.classList.toggle("hidden", !isLogin);
  panelRegister.classList.toggle("hidden", isLogin);

  clearAuthErrors();
}

/* ─── Hata Gösterimi ──────────────────────────────────────── */

function showAuthError(el, msg) {
  el.textContent = msg;
  el.classList.remove("hidden");
}

function clearAuthErrors() {
  [loginError, registerError].forEach(el => {
    el.textContent = "";
    el.classList.add("hidden");
  });
}

/* ─── Yükleniyor Durumu ───────────────────────────────────── */

function setSubmitLoading(btn, loading) {
  const text    = btn.querySelector(".auth-btn-text");
  const spinner = btn.querySelector(".auth-spinner");
  btn.disabled  = loading;
  text.classList.toggle("hidden", loading);
  spinner.classList.toggle("hidden", !loading);
}

/* ─── Şifre Göster/Gizle ──────────────────────────────────── */

function togglePasswordVisibility(btn) {
  const targetId = btn.dataset.target;
  const input    = document.getElementById(targetId);
  if (!input) return;

  const isHidden = input.type === "password";
  input.type = isHidden ? "text" : "password";

  // İkon güncelle
  const svg = btn.querySelector("svg");
  if (svg) {
    svg.innerHTML = isHidden
      ? `<path d="M13.875 9.125C13.027 10.69 11.12 12.5 8 12.5c-3.12 0-5.027-1.81-5.875-3.375"/>
         <path d="M2 2l12 12" stroke-linecap="round"/>` // gizli ikon
      : `<path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z"/>
         <circle cx="8" cy="8" r="2"/>`; // açık ikon
  }
}

/* ─── Auth UI Güncelleme ──────────────────────────────────── */

function updateAuthUI() {
  const loggedIn = isAuthenticated();
  const user     = getAuthUser();

  // Giriş / chip görünürlüğü
  if (btnLogin)    btnLogin.classList.toggle("hidden", loggedIn);
  if (authUserChip) authUserChip.classList.toggle("hidden", !loggedIn);

  if (loggedIn && user) {
    // Kullanıcı adını ve avatar baş harfini güncelle
    const display = user.full_name || user.email || "Kullanıcı";
    if (authUsername) authUsername.textContent = display;
    if (authAvatar) {
      authAvatar.textContent = display.charAt(0).toUpperCase();
    }
  }
}

/* ─── Giriş İşlemi ────────────────────────────────────────── */

async function handleLogin(e) {
  e.preventDefault();
  clearAuthErrors();

  const email    = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  if (!email || !password) {
    showAuthError(loginError, "E-posta ve şifre zorunludur.");
    return;
  }

  setSubmitLoading(btnLoginSubmit, true);

  try {
    const res = await apiLogin(email, password);
    setAuthToken(res.access_token);
    setAuthUser({ email: res.email, full_name: res.full_name });
    updateAuthUI();
    closeAuthModal();
    showToast(`Hoş geldiniz, ${res.full_name || res.email}!`, "success");
  } catch (err) {
    showAuthError(loginError, err.message || "Giriş başarısız. Bilgilerinizi kontrol edin.");
  } finally {
    setSubmitLoading(btnLoginSubmit, false);
  }
}

/* ─── Kayıt İşlemi ────────────────────────────────────────── */

async function handleRegister(e) {
  e.preventDefault();
  clearAuthErrors();

  const fullName = document.getElementById("registerName").value.trim() || null;
  const email    = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;

  if (!email || !password) {
    showAuthError(registerError, "E-posta ve şifre zorunludur.");
    return;
  }
  if (password.length < 6) {
    showAuthError(registerError, "Şifre en az 6 karakter olmalıdır.");
    return;
  }

  setSubmitLoading(btnRegisterSubmit, true);

  try {
    const res = await apiRegister(email, password, fullName);
    setAuthToken(res.access_token);
    setAuthUser({ email: res.email, full_name: res.full_name });
    updateAuthUI();
    closeAuthModal();
    showToast(`Hesabınız oluşturuldu. Hoş geldiniz, ${res.full_name || res.email}!`, "success");
  } catch (err) {
    showAuthError(registerError, err.message || "Kayıt başarısız. Lütfen tekrar deneyin.");
  } finally {
    setSubmitLoading(btnRegisterSubmit, false);
  }
}

/* ─── Çıkış İşlemi ────────────────────────────────────────── */

function handleLogout() {
  apiLogout();
  updateAuthUI();
  showToast("Başarıyla çıkış yapıldı.", "info");
}

/* ─── showToast fallback ──────────────────────────────────── */
// app.js henüz yüklenmemişse minimal toast; app.js yüklenince override edilir.
function showToast(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 350);
  }, 3500);
}

/* ─── Event Listener'lar ──────────────────────────────────── */

// Modal açma butonu
if (btnLogin) {
  btnLogin.addEventListener("click", () => openAuthModal("login"));
}

// Çıkış butonu
if (btnLogout) {
  btnLogout.addEventListener("click", handleLogout);
}

// Tab değiştirme
[tabLogin, tabRegister].forEach(tab => {
  tab.addEventListener("click", () => switchAuthTab(tab.dataset.tab));
});

// "Hesabınız yok mu?" / "Zaten hesabınız var mı?" linkleri
document.querySelectorAll(".auth-switch-link").forEach(link => {
  link.addEventListener("click", () => switchAuthTab(link.dataset.switch));
});

// Form submit
if (loginForm)    loginForm.addEventListener("submit", handleLogin);
if (registerForm) registerForm.addEventListener("submit", handleRegister);

// Şifre göster/gizle toggle'ları
document.querySelectorAll(".auth-pw-toggle").forEach(btn => {
  btn.addEventListener("click", () => togglePasswordVisibility(btn));
});

// Modal dışına tıklayınca kapat
if (authModal) {
  authModal.addEventListener("click", e => {
    if (e.target === authModal) closeAuthModal();
  });
}

// ESC tuşu ile kapat
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && authModal && authModal.style.display !== "none") {
    closeAuthModal();
  }
});

/* ─── Sayfa yüklenince token kontrol ─────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  updateAuthUI();
});
