const API = {
  auth: "/api/auth",
  courses: "/api/courses",
  progress: "/api/progress",
};

function saveToken(token) {
  localStorage.setItem("access_token", token);
}

function getToken() {
  return localStorage.getItem("access_token");
}

async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = options.headers ? { ...options.headers } : {};
  if (token) headers["Authorization"] = "Bearer " + token;
  return fetch(url, { ...options, headers });
}

async function loadCurrentUser() {
  const el = document.getElementById("current-user");
  if (!el) return;
  const token = getToken();
  if (!token) {
    el.innerHTML = `<span>Вы не вошли в аккаунт</span>`;
    return;
  }
  try {
    const res = await authFetch(`${API.auth}/me`);
    if (!res.ok) throw new Error("Ошибка");
    const data = await res.json();
    el.innerHTML = `
      <div class="user-pill">
        <span>👤 ${data.email}</span>
        <span class="user-pill-role">${data.role}</span>
      </div>
    `;
  } catch {
    localStorage.removeItem("access_token");
    el.innerHTML = `<span>Вы не вошли в аккаунт</span>`;
  }
}


/* --- index.html логика --- */

function initIndexPage() {
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const status = document.getElementById("auth-status");
  const coursesList = document.getElementById("courses-list");

  async function handleLogin(e) {
    e.preventDefault();
    status.textContent = "Выполняем вход...";
    const email = loginForm.email.value.trim();
    const password = loginForm.password.value;

    try {
        const res = await fetch(`${API.auth}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Не удалось войти");
    }
    const data = await res.json();
    saveToken(data.access_token);

    await loadCurrentUser();
    await loadCourses();

    status.textContent = "Успешный вход ✅";
    } 
    catch (err) {
        status.innerHTML = `<span class="error">${err.message}</span>`;
    }
}

  async function handleRegister(e) {
    e.preventDefault();
    status.textContent = "Регистрируем пользователя...";
    const email = registerForm.email.value.trim();
    const password = registerForm.password.value;
    try {
      const res = await fetch(`${API.auth}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Ошибка регистрации");
      }
      status.textContent = "Регистрация успешна, выполняем вход...";
      // после регистрации сразу логинимся
      const loginRes = await fetch(`${API.auth}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const loginData = await loginRes.json();
      saveToken(loginData.access_token);
      await loadCurrentUser();
      await loadCourses();
      status.textContent = "Готово ✅";
    } catch (err) {
      status.innerHTML = `<span class="error">${err.message}</span>`;
    }
  }

  async function loadCourses() {
    if (!coursesList) return;
    coursesList.innerHTML = "Загружаем курсы...";
    try {
      const res = await fetch(`${API.courses}?limit=20&offset=0`);
      if (!res.ok) throw new Error("Ошибка загрузки курсов");
      const data = await res.json();
      if (!data.length) {
        coursesList.innerHTML = `<span class="muted">Пока нет курсов.</span>`;
        return;
      }
      coursesList.innerHTML = "";
      data.forEach((c) => {
        const div = document.createElement("div");
        div.className = "list-item";
        div.innerHTML = `
          <div class="list-main">
            <div class="list-title">${c.title}</div>
            <div class="list-desc">${c.description ?? ""}</div>
          </div>
          <div>
            <a class="btn-outline btn" href="course.html?id=${c.id}">Открыть</a>
          </div>
        `;
        coursesList.appendChild(div);
      });
    } catch (err) {
      coursesList.innerHTML = `<span class="error">${err.message}</span>`;
    }
  }

  if (loginForm) loginForm.addEventListener("submit", handleLogin);
  if (registerForm) registerForm.addEventListener("submit", handleRegister);

  loadCurrentUser();
  loadCourses();
}

/* --- course.html логика --- */

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function initCoursePage() {
  const courseTitleEl = document.getElementById("course-title");
  const lessonsList = document.getElementById("lessons-list");
  const infoBar = document.getElementById("course-info");
  const courseId = getQueryParam("id");

  if (!courseId) {
    if (infoBar) infoBar.innerHTML = `<span class="error">Не указан id курса.</span>`;
    return;
  }

  async function loadLessons() {
    lessonsList.innerHTML = "Загружаем уроки...";
    try {
      const coursesRes = await fetch(`${API.courses}?limit=50&offset=0`);
      const courses = await coursesRes.json();
      const course = courses.find((c) => String(c.id) === String(courseId));
      if (courseTitleEl && course) {
        courseTitleEl.textContent = course.title;
      }

      const res = await fetch(`${API.courses}/${courseId}/lessons`);
      if (!res.ok) throw new Error("Ошибка загрузки уроков");
      const data = await res.json();
      if (!data.length) {
        lessonsList.innerHTML = `<span class="muted">У этого курса пока нет уроков.</span>`;
        return;
      }

      lessonsList.innerHTML = "";
      data.forEach((l) => {
        const div = document.createElement("div");
        div.className = "list-item";
        div.innerHTML = `
          <div class="list-main">
            <div class="list-title">Урок ${l.order}: ${l.title}</div>
          </div>
          <button class="btn btn-sm" data-lesson-id="${l.id}">Просмотрено</button>
        `;
        lessonsList.appendChild(div);
      });

      lessonsList.addEventListener("click", async (e) => {
        const btn = e.target.closest("button[data-lesson-id]");
        if (!btn) return;
        const lessonId = btn.getAttribute("data-lesson-id");
        try {
          const res = await authFetch(`${API.progress}/${lessonId}/complete`, {
            method: "POST",
          });
          if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.detail || "Ошибка отметки прогресса");
          }
          btn.textContent = "✓ Просмотрено";
          btn.disabled = true;
        } catch (err) {
          infoBar.innerHTML = `<span class="error">${err.message}</span>`;
        }
      });
    } catch (err) {
      lessonsList.innerHTML = `<span class="error">${err.message}</span>`;
    }
  }

  loadCurrentUser();
  loadLessons();
}

/* --- progress.html логика --- */

function initProgressPage() {
  const list = document.getElementById("timeline");
  const info = document.getElementById("progress-info");

  async function loadProgress() {
    list.innerHTML = "Загружаем прогресс...";
    try {
      const res = await authFetch(`${API.progress}/my?limit=100&offset=0`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Ошибка загрузки прогресса");
      }
      const data = await res.json();
      if (!data.length) {
        list.innerHTML = `<span class="muted">Пока нет отмеченных уроков.</span>`;
        return;
      }
      list.innerHTML = "";
      data.forEach((item) => {
        const div = document.createElement("div");
        div.className = "timeline-item";
        const date = new Date(item.completed_at);
        div.innerHTML = `
          <div class="timeline-title">Урок ${item.lesson_id}</div>
          <div class="timeline-date">${date.toLocaleString()}</div>
        `;
        list.appendChild(div);
      });
    } catch (err) {
      list.innerHTML = `<span class="error">${err.message}</span>`;
    }
  }

  loadCurrentUser();
  loadProgress();
}

/* --- Инициализация по data-page --- */

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  switch (page) {
    case "index":
      initIndexPage();
      break;
    case "course":
      initCoursePage();
      break;
    case "progress":
      initProgressPage();
      break;
    default:
      loadCurrentUser();
  }
});
