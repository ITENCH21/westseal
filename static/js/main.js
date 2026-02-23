// === Mobile nav toggle ===
const navToggle = document.querySelector('#nav-toggle');
const mainNav = document.querySelector('#main-nav');
if (navToggle && mainNav) {
  const openNav = () => {
    mainNav.classList.add('is-open');
    navToggle.classList.add('is-open');
    navToggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('no-scroll', 'nav-is-open');
  };
  const closeNav = () => {
    mainNav.classList.remove('is-open');
    navToggle.classList.remove('is-open');
    navToggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('no-scroll', 'nav-is-open');
  };
  navToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    mainNav.classList.contains('is-open') ? closeNav() : openNav();
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#main-nav') && !e.target.closest('#nav-toggle')) {
      closeNav();
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeNav();
  });
  // Close nav on link click (for mobile navigation)
  mainNav.querySelectorAll('a').forEach((a) => {
    a.addEventListener('click', () => closeNav());
  });
}

// === Бесконечный двунаправленный скролл тикеров ===
// 3 набора пунктов, старт в set 2 (середине).
// Буфер MARGIN = 20% от W гарантирует что даже быстрый momentum-scroll
// словит сброс до того как упрётся в стену.
(function initInfiniteTickers() {
  const TICKERS = [
    { wrapId: 'nav-menu-ticker-wrap',    trackId: 'nav-menu-ticker-track',   speed: 0.4  },
    { wrapId: 'catalog-ticker-wrap',     trackId: 'catalog-ticker-track',    speed: -0.35 },
    { wrapId: 'catalog-subticker-outer', trackId: 'catalog-subticker-track', speed: 0.3  },
  ];

  TICKERS.forEach(({ wrapId, trackId, speed }) => {
    const wrap  = document.getElementById(wrapId);
    const track = document.getElementById(trackId);
    if (!wrap || !track || track.children.length === 0) return;

    // 3 набора: оригинал + 2 клона → есть буфер в обе стороны
    // Клоны скрыты от AT через inert-обёртку (aria-hidden не на <a>-элементах).
    const originals = Array.from(track.children);
    [0, 1].forEach(() => {
      // Один inert-контейнер на весь набор клонов → display:contents
      // сохраняет flex-раскладку, inert + aria-hidden убирают из AT и фокуса.
      const ghost = document.createElement('span');
      ghost.setAttribute('aria-hidden', 'true');
      ghost.setAttribute('inert', '');
      ghost.style.cssText = 'display:contents';
      originals.forEach((item) => ghost.appendChild(item.cloneNode(true)));
      track.appendChild(ghost);
    });

    const storageKey = 'ticker_pos_' + wrapId;

    requestAnimationFrame(() => {
      const W = track.scrollWidth / 3;  // ширина одного набора
      if (W < 10) return;

      // MARGIN: чем больше — тем раньше ловим рывок до стены.
      // 20% W надёжно покрывает любой momentum на iOS/Android.
      const MARGIN = Math.max(80, W * 0.20);

      // Восстанавливаем смещение внутри одного набора → позиция в set 2
      const saved  = sessionStorage.getItem(storageKey);
      const offset = saved !== null ? parseFloat(saved) % W : 0;
      wrap.scrollLeft = W + (isNaN(offset) ? 0 : offset);

      // Сохраняем смещение внутри набора при клике
      wrap.addEventListener('click', (e) => {
        if (e.target.closest('a[href]') && !e.defaultPrevented) {
          sessionStorage.setItem(storageKey, ((wrap.scrollLeft % W) + W) % W);
        }
      });

      // Бесконечный цикл: вправо и влево
      wrap.addEventListener('scroll', () => {
        const sl = wrap.scrollLeft;
        if (sl >= W * 2) {
          wrap.scrollLeft = sl - W;   // ушли за set 3 → тихо назад на W
        } else if (sl < MARGIN) {
          wrap.scrollLeft = sl + W;   // приближаемся к 0 → вперёд на W
        }
      }, { passive: true });

      // Mouse-drag (десктоп/превью; тач работает через overflow-x: auto)
      let isDragging = false, startX = 0, startSL = 0, moved = false;

      track.addEventListener('mousedown', (e) => {
        isDragging = true; moved = false;
        startX = e.clientX; startSL = wrap.scrollLeft;
        track.style.cursor = 'grabbing';
        e.preventDefault();
      });
      document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        if (Math.abs(dx) > 3) moved = true;
        wrap.scrollLeft = startSL - dx;
      });
      document.addEventListener('mouseup', () => {
        if (!isDragging) return;
        isDragging = false;
        track.style.cursor = 'grab';
      });

      // Блокируем переход по ссылке если был drag, а не tap
      track.querySelectorAll('a').forEach((a) => {
        a.addEventListener('click', (e) => { if (moved) e.preventDefault(); });
      });

      // === Auto-scroll: медленное непрерывное движение ===
      const dir = speed || 0.4;
      let paused = false;
      let pauseTimer = null;

      const pauseAutoScroll = () => {
        paused = true;
        clearTimeout(pauseTimer);
        pauseTimer = setTimeout(() => { paused = false; }, 2000);
      };

      // Пауза при touch / drag
      wrap.addEventListener('touchstart', pauseAutoScroll, { passive: true });
      wrap.addEventListener('mousedown', pauseAutoScroll);
      wrap.addEventListener('wheel', pauseAutoScroll, { passive: true });

      // rAF loop
      let lastTime = 0;
      const autoScroll = (now) => {
        if (!lastTime) lastTime = now;
        const dt = now - lastTime;
        lastTime = now;
        if (!paused && dt < 100) { // skip big gaps (tab was hidden)
          wrap.scrollLeft += dir * (dt / 16); // normalize to ~60fps
        }
        requestAnimationFrame(autoScroll);
      };
      requestAnimationFrame(autoScroll);
    });
  });
})();

const counters = document.querySelectorAll('[data-counter]');
const runCounter = (el) => {
  const target = parseInt(el.dataset.counter, 10) || 0;
  let current = 0;
  const step = Math.max(1, Math.ceil(target / 40));
  const tick = () => {
    current += step;
    if (current >= target) {
      el.textContent = target;
      return;
    }
    el.textContent = current;
    requestAnimationFrame(tick);
  };
  tick();
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      runCounter(entry.target);
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.6 });

counters.forEach((el) => observer.observe(el));

const revealEls = document.querySelectorAll(".reveal");
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("is-visible");
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.2 });
revealEls.forEach((el) => revealObserver.observe(el));

const tiltCards = document.querySelectorAll(".tilt");
tiltCards.forEach((card) => {
  card.addEventListener("mousemove", (e) => {
    const rect = card.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    card.style.transform = `rotateX(${y * -8}deg) rotateY(${x * 10}deg) translateY(-4px)`;
  });
  card.addEventListener("mouseleave", () => {
    card.style.transform = "rotateX(0) rotateY(0) translateY(0)";
  });
});

const hotspotData = {
  rod: {
    title: "Уплотнение штока",
    body: "Герметизация штока под давлением, защита от утечек и износа.",
    bullets: ["Профили U-манжеты", "Материалы NBR / PU / FKM", "Контроль давления и скорости"],
  },
  piston: {
    title: "Уплотнение поршня",
    body: "Двусторонняя герметизация поршня, устойчивость к перепадам давления.",
    bullets: ["Кольца и композиты", "PTFE с наполнителями", "Минимизация трения"],
  },
  wiper: {
    title: "Грязесъемник",
    body: "Защита цилиндра от абразива и пыли, продление ресурса.",
    bullets: ["PU и резины", "Работа в грязных средах", "Стабильная геометрия"],
  },
};

const panel = document.querySelector("[data-hotspot-panel]");
if (panel) {
  const title = panel.querySelector("[data-hotspot-title]");
  const body = panel.querySelector("[data-hotspot-body]");
  const list = panel.querySelector(".bullets");
  document.querySelectorAll(".hotspot, .hotspot-pin").forEach((spot) => {
    const key = spot.dataset.hotspot;
    spot.addEventListener("mouseenter", () => {
      const data = hotspotData[key];
      if (!data) return;
      title.textContent = data.title;
      body.textContent = data.body;
      list.innerHTML = data.bullets.map((b) => `<li>${b}</li>`).join("");
    });
    spot.addEventListener("click", () => {
      const data = hotspotData[key];
      if (!data) return;
      title.textContent = data.title;
      body.textContent = data.body;
      list.innerHTML = data.bullets.map((b) => `<li>${b}</li>`).join("");
    });
  });
}

// Lottie initialization moved to home.html for deferred loading

document.querySelectorAll(".flip-card").forEach((card) => {
  card.addEventListener("click", () => {
    card.classList.toggle("is-flipped");
  });
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      card.classList.toggle("is-flipped");
    }
  });
});

const stickyCta = document.querySelector(".sticky-cta");
if (stickyCta) {
  let hideTimer = null;
  const show = () => {
    stickyCta.classList.add("is-visible");
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      stickyCta.classList.remove("is-visible");
    }, 1400);
  };
  ["mousemove", "scroll", "touchstart", "keydown"].forEach((evt) => {
    window.addEventListener(evt, show, { passive: true });
  });
  show();
}

const chatOpenBtn = document.querySelector("#chat-open-btn");
const chatHideBtn = document.querySelector("#chat-hide-btn");
const chatDrawer = document.querySelector("#chat-drawer");
const chatGreeting = document.querySelector("#chat-greeting");
const chatFrame = document.querySelector("#chat-frame");
if (chatOpenBtn && chatHideBtn && chatDrawer) {
  const openChat = () => {
    trackEvent("chat_open", { location: window.location.pathname });
    if (chatFrame) {
      const url = new URL(chatFrame.getAttribute("src"), window.location.origin);
      url.searchParams.set("_ts", String(Date.now()));
      chatFrame.setAttribute("src", `${url.pathname}${url.search}`);
    }
    chatDrawer.classList.add("is-open");
    chatDrawer.setAttribute("aria-hidden", "false");
    chatDrawer.removeAttribute("inert");
    document.body.classList.add("no-scroll");
    const greeted = sessionStorage.getItem("chat_greeted") === "1";
    if (!greeted && chatGreeting) {
      setTimeout(() => {
        chatGreeting.classList.add("is-visible");
      }, 1000);
      sessionStorage.setItem("chat_greeted", "1");
    }
  };
  const hideChat = () => {
    trackEvent("chat_hide", { location: window.location.pathname });
    chatDrawer.classList.remove("is-open");
    chatDrawer.setAttribute("aria-hidden", "true");
    chatDrawer.setAttribute("inert", "");
    document.body.classList.remove("no-scroll");
  };
  chatOpenBtn.addEventListener("click", openChat);
  chatHideBtn.addEventListener("click", hideChat);
}

const leadModal = document.querySelector("#lead-modal");
if (leadModal) {
  const openLead = () => {
    leadModal.classList.add("is-open");
    leadModal.setAttribute("aria-hidden", "false");
    leadModal.removeAttribute("inert");
    document.body.classList.add("no-scroll");
    trackEvent("quick_lead_open", { location: window.location.pathname });
  };
  const closeLead = () => {
    leadModal.classList.remove("is-open");
    leadModal.setAttribute("aria-hidden", "true");
    leadModal.setAttribute("inert", "");
    document.body.classList.remove("no-scroll");
  };
  document.querySelectorAll("[data-open-lead]").forEach((btn) => btn.addEventListener("click", openLead));
  leadModal.querySelectorAll("[data-close-lead]").forEach((btn) => btn.addEventListener("click", closeLead));
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeLead();
  });
}

function trackEvent(name, params = {}) {
  if (window.gtag) {
    window.gtag("event", name, params);
  }
  if (window.ym && window.__YANDEX_ID) {
    window.ym(window.__YANDEX_ID, "reachGoal", name);
  }
}

document.addEventListener("click", (e) => {
  const tracked = e.target.closest("[data-track]");
  if (!tracked) return;
  trackEvent(tracked.getAttribute("data-track"), { location: window.location.pathname });
});

const themeToggle = document.querySelector(".theme-toggle");
const allThemeToggles = document.querySelectorAll(".theme-toggle, .nav-theme-toggle");
const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
const savedTheme = localStorage.getItem("theme");
const applyTheme = (theme) => {
  document.body.classList.toggle("theme-dark", theme === "dark");
  allThemeToggles.forEach((btn) => { btn.textContent = theme === "dark" ? "☀" : "◐"; });
};
if (savedTheme) {
  applyTheme(savedTheme);
} else if (prefersDark) {
  applyTheme("dark");
}
allThemeToggles.forEach((btn) => {
  btn.addEventListener("click", () => {
    const isDark = document.body.classList.contains("theme-dark");
    const next = isDark ? "light" : "dark";
    localStorage.setItem("theme", next);
    applyTheme(next);
  });
});

const chatLog = document.querySelector("[data-chat-log]");
const chatForm = document.querySelector("[data-chat-form]");
if (chatLog && chatForm) {
  const apiUrl = chatLog.getAttribute("data-chat-api");
  const wsPath = chatLog.getAttribute("data-chat-ws");
  const meEmail = (chatLog.getAttribute("data-chat-me") || "").trim().toLowerCase();
  const bodyInput = chatForm.querySelector("textarea") || chatForm.querySelector("input[name='body']");
  const fileInput = chatForm.querySelector("input[type='file']");
  const sendBtn = chatForm.querySelector("button[type='submit']");
  const attachBtnLabel = chatForm.querySelector(`label[for="${fileInput ? fileInput.id : ""}"]`);

  const timeOnly = (value) => {
    const match = String(value || "").match(/(\d{2}:\d{2})\s*$/);
    return match ? match[1] : "";
  };
  const formatText = (value) => {
    const normalized = (value || "").trim();
    if (!normalized) return "";
    return normalized
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br>");
  };
  const escapeHtml = (value) => (value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  const renderAttachments = (files) => {
    if (!Array.isArray(files) || !files.length) return "";
    const items = files.map((f) => {
      const safeUrl = escapeHtml(f.url || "");
      const safeName = escapeHtml(f.name || "file");
      if (f.type === "image") {
        return `<a href="${safeUrl}" target="_blank" class="attachment-card"><img src="${safeUrl}" alt="attachment"></a>`;
      }
      if (f.type === "video") {
        return `<div class="attachment-card"><video src="${safeUrl}" controls></video></div>`;
      }
      return `<a href="${safeUrl}" target="_blank" class="attachment-file">${safeName}</a>`;
    }).join("");
    return `<div class="attachments-grid">${items}</div>`;
  };
  const appendMessage = (msg) => {
    const msgId = Number(msg.id || 0);
    if (msgId > 0 && chatLog.querySelector(`.chat-line[data-message-id="${msgId}"]`)) return;
    const authorEmail = String(msg.author || "").trim().toLowerCase();
    const isBot = msg.is_bot === true || msg.via === "bot";
    const isAdmin = !isBot && (msg.via === "admin" || msg.via === "telegram");
    const isMine = !isBot && !isAdmin;
    const lineClass = isBot ? "bot" : isAdmin ? "admin" : "mine";
    const line = document.createElement("div");
    line.className = `chat-line ${lineClass}`.trim();
    line.setAttribute("data-message-id", String(msgId || ""));
    line.innerHTML = `
      <div class="chat-bubble">
        <div class="chat-bubble-text">
          ${formatText(msg.body)}
          ${renderAttachments(msg.attachments)}
        </div>
        <span class="chat-time">${escapeHtml(timeOnly(msg.created))}</span>
      </div>
    `;
    chatLog.appendChild(line);
  };
  const getLastId = () => {
    const items = chatLog.querySelectorAll(".chat-line[data-message-id]");
    if (!items.length) return 0;
    return Number(items[items.length - 1].getAttribute("data-message-id") || 0);
  };
  const shouldStickToBottom = () => chatLog.scrollHeight - chatLog.scrollTop - chatLog.clientHeight < 120;
  const scrollToBottom = () => {
    chatLog.scrollTop = chatLog.scrollHeight;
  };
  const fetchMissed = async () => {
    if (!apiUrl) return;
    try {
      const before = shouldStickToBottom();
      const res = await fetch(`${apiUrl}?after_id=${getLastId()}`, { credentials: "same-origin" });
      if (!res.ok) return;
      const data = await res.json();
      if (!Array.isArray(data.messages) || !data.messages.length) return;
      data.messages.forEach((msg) => appendMessage(msg));
      if (before) scrollToBottom();
    } catch (_e) {
      // silent background sync errors
    }
  };

  let ws = null;
  let reconnectTimer = null;
  const connectWebSocket = () => {
    if (!wsPath) return;
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${scheme}://${window.location.host}${wsPath}`);
    ws.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data || "{}");
        if (!payload || !payload.id) return;
        const before = shouldStickToBottom();
        appendMessage(payload);
        if (before) scrollToBottom();
      } catch (_e) {
        // ignore invalid ws packets
      }
    });
    ws.addEventListener("close", () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(() => {
        fetchMissed();
        connectWebSocket();
      }, 1400);
    });
  };

  scrollToBottom();
  connectWebSocket();
  window.addEventListener("beforeunload", () => {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (ws && ws.readyState === WebSocket.OPEN) ws.close();
  });

  const quick = document.querySelector("[data-chat-quick]");
  if (quick && bodyInput) {
    quick.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-chat-quick-text],[data-chat-quick-focus]");
      if (!btn) return;
      if (btn.hasAttribute("data-chat-quick-focus")) {
        bodyInput.focus();
        return;
      }
      const text = btn.getAttribute("data-chat-quick-text") || "";
      bodyInput.value = text;
      chatForm.requestSubmit ? chatForm.requestSubmit() : chatForm.submit();
    });
  }

  const emojiBtn = chatForm.querySelector("[data-chat-emoji]");
  if (emojiBtn && bodyInput) {
    emojiBtn.addEventListener("click", () => {
      const emoji = "🙂";
      const start = bodyInput.selectionStart ?? bodyInput.value.length;
      const end = bodyInput.selectionEnd ?? bodyInput.value.length;
      bodyInput.value = `${bodyInput.value.slice(0, start)}${emoji}${bodyInput.value.slice(end)}`;
      try {
        bodyInput.setSelectionRange(start + emoji.length, start + emoji.length);
      } catch (_e) {
        // ignore
      }
      bodyInput.focus();
    });
  }

  if (fileInput && attachBtnLabel) {
    const syncFilesState = () => {
      const hasFiles = Boolean(fileInput.files && fileInput.files.length);
      attachBtnLabel.classList.toggle("has-files", hasFiles);
    };
    fileInput.addEventListener("change", syncFilesState);
    syncFilesState();
  }

  // Submit without full page reload (server redirects, but we just treat it as success).
  chatForm.addEventListener("submit", async (e) => {
    if (!apiUrl) return; // fallback to normal submit
    e.preventDefault();
    if (sendBtn) sendBtn.disabled = true;
    try {
      const formData = new FormData(chatForm);
      const res = await fetch(chatForm.getAttribute("action") || window.location.href, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
      });
      if (!res.ok) return;
      if (bodyInput) bodyInput.value = "";
      if (fileInput) fileInput.value = "";
      if (attachBtnLabel) attachBtnLabel.classList.remove("has-files");
      await fetchMissed();
      scrollToBottom();
    } catch (_e) {
      // ignore
    } finally {
      if (sendBtn) sendBtn.disabled = false;
    }
  });
}
