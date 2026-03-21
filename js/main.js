/* ============================================================
   ARKHE — Main JavaScript
   ============================================================ */

(function () {
  'use strict';

  /* ---- DOM Ready ---- */
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    initTheme();
    initHeader();
    initMobileMenu();
    initScrollProgress();
    initTOC();
    initNewsletter();
    // columnsGrid があればカードを動的ロード、なければ（記事ページ）直接初期化
    if (document.getElementById('columnsGrid')) {
      loadArticles();
    } else {
      initReveal();
      initFilters();
    }
  }

  /* ============================================================
     THEME (Light / Dark)
     ============================================================ */
  function initTheme() {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;

    const stored = localStorage.getItem('arkhe-theme');
    const prefDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefDark ? 'dark' : 'light');
    applyTheme(theme);

    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('arkhe-theme', theme);
  }

  /* ============================================================
     HEADER — Scroll Effect
     ============================================================ */
  function initHeader() {
    const header = document.getElementById('header');
    if (!header) return;

    let lastY = 0;
    let ticking = false;

    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const y = window.scrollY;
          if (y > 40) {
            header.classList.add('scrolled');
          } else {
            header.classList.remove('scrolled');
          }
          // Hide on scroll down, show on scroll up (beyond hero)
          if (y > 300) {
            if (y > lastY + 5) {
              header.style.transform = 'translateY(-100%)';
            } else if (y < lastY - 5) {
              header.style.transform = 'translateY(0)';
            }
          } else {
            header.style.transform = 'translateY(0)';
          }
          lastY = y;
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* ============================================================
     MOBILE MENU
     ============================================================ */
  function initMobileMenu() {
    const toggle = document.getElementById('menuToggle');
    const menu = document.getElementById('mobileMenu');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
      const isOpen = menu.classList.contains('open');
      menu.classList.toggle('open', !isOpen);
      toggle.classList.toggle('open', !isOpen);
      document.body.style.overflow = isOpen ? '' : 'hidden';
    });

    // Close on link click
    menu.querySelectorAll('.mobile-nav-link').forEach(link => {
      link.addEventListener('click', () => {
        menu.classList.remove('open');
        toggle.classList.remove('open');
        document.body.style.overflow = '';
      });
    });

    // Close on backdrop click
    menu.addEventListener('click', (e) => {
      if (e.target === menu) {
        menu.classList.remove('open');
        toggle.classList.remove('open');
        document.body.style.overflow = '';
      }
    });
  }

  /* ============================================================
     SCROLL PROGRESS BAR
     ============================================================ */
  function initScrollProgress() {
    const bar = document.getElementById('scrollProgress') || document.getElementById('readProgress');
    if (!bar) return;

    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      bar.style.width = `${Math.min(progress, 100)}%`;
    }, { passive: true });
  }

  /* ============================================================
     REVEAL ON SCROLL (Intersection Observer)
     ============================================================ */
  function initReveal() {
    const items = document.querySelectorAll('.reveal');
    if (!items.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.08,
      rootMargin: '0px 0px -40px 0px'
    });

    items.forEach(el => observer.observe(el));
  }

  /* ============================================================
     CATEGORY FILTERS
     ============================================================ */
  function initFilters() {
    const tabs = document.querySelectorAll('.filter-tab');
    const grid = document.getElementById('columnsGrid');
    if (!tabs.length || !grid) return;

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        const filter = tab.dataset.filter;
        const cards = grid.querySelectorAll('.column-card');

        cards.forEach((card, i) => {
          const match = filter === 'all' || card.dataset.category === filter;
          card.classList.toggle('hidden', !match);
          if (match) {
            // Stagger re-reveal
            card.classList.remove('visible');
            setTimeout(() => {
              card.classList.add('visible');
            }, i * 60);
          }
        });
      });
    });

    // Make all visible initially
    setTimeout(() => {
      document.querySelectorAll('.column-card').forEach(c => c.classList.add('visible'));
    }, 100);
  }

  /* ============================================================
     TABLE OF CONTENTS — Active Link Tracking
     ============================================================ */
  function initTOC() {
    const tocLinks = document.querySelectorAll('.toc-link');
    if (!tocLinks.length) return;

    const sections = Array.from(tocLinks).map(link => {
      const id = link.getAttribute('href').replace('#', '');
      return document.getElementById(id);
    }).filter(Boolean);

    if (!sections.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const id = entry.target.id;
          tocLinks.forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === `#${id}`);
          });
        }
      });
    }, {
      rootMargin: '-20% 0px -70% 0px',
      threshold: 0
    });

    sections.forEach(s => observer.observe(s));
  }

  /* ============================================================
     NEWSLETTER FORM
     ============================================================ */
  function initNewsletter() {
    const form = document.getElementById('newsletterForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = form.querySelector('.form-input');
      const btn = form.querySelector('.btn-submit span');
      if (!input || !btn) return;

      const original = btn.textContent;
      btn.textContent = '送信中…';
      input.disabled = true;

      try {
        const res = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { 'Accept': 'application/json' }
        });

        if (res.ok) {
          btn.textContent = '登録完了 ✓';
          input.value = '';
          setTimeout(() => {
            btn.textContent = original;
            input.disabled = false;
          }, 4000);
        } else {
          btn.textContent = 'エラーが発生しました';
          input.disabled = false;
          setTimeout(() => { btn.textContent = original; }, 3000);
        }
      } catch {
        btn.textContent = 'エラーが発生しました';
        input.disabled = false;
        setTimeout(() => { btn.textContent = original; }, 3000);
      }
    });
  }

  /* ============================================================
     LOAD ARTICLES from articles.json
     ============================================================ */
  async function loadArticles() {
    const grid = document.getElementById('columnsGrid');
    if (!grid) return;
    try {
      const res = await fetch('articles.json?v=' + Date.now(), { cache: 'no-store' });
      const data = await res.json();
      grid.innerHTML = data.articles
        .map((a, i) => renderCard(a, i + 1))
        .join('');
      updateStats(data.articles);
      updateHero(data.articles);
      initFilters();
      initReveal();
    } catch (e) {
      console.error('Failed to load articles:', e);
      grid.innerHTML = '<p style="text-align:center;padding:3rem;opacity:.5">読み込みに失敗しました</p>';
    }
  }

  function updateStats(articles) {
    const colEl  = document.getElementById('statColumns');
    const authEl = document.getElementById('statAuthors');
    const catEl  = document.getElementById('statCategories');
    if (colEl)  colEl.textContent  = articles.length;
    if (authEl) authEl.textContent = new Set(articles.map(a => a.author.name)).size;
    if (catEl)  catEl.textContent  = new Set(articles.map(a => a.category)).size;
  }

  function updateHero(articles) {
    const featured = articles.find(a => a.featured) || articles[0];
    if (!featured) return;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    const setAttr = (id, attr, val) => { const el = document.getElementById(id); if (el) el.setAttribute(attr, val); };
    const setHtml = (id, val) => { const el = document.getElementById(id); if (el) el.innerHTML = val; };

    setAttr('heroImg',  'src', featured.heroImage);
    setAttr('heroImg',  'alt', featured.title);
    set('heroTag',        featured.categoryLabel);
    setHtml('heroTitle',  featured.titleHtml);
    set('heroExcerpt',    featured.excerpt);
    set('heroAvatar',     featured.author.avatarChar);
    set('heroAuthorName', featured.author.name);
    set('heroAuthorRole', featured.author.role);
    set('heroDate',       featured.dateFormatted);
    set('heroReadTime',   featured.readTime);
    setAttr('heroLink', 'href', 'articles/' + featured.slug + '.html');
    set('heroCounterTotal', articles.length);
  }

    function renderCard(a, num) {
    const classes = ['column-card', a.cardLayout, 'reveal']
      .filter(Boolean).join(' ');
    const n = String(num).padStart(2, '0');
    return `
    <article class="${classes}" data-category="${a.category}">
      <a href="articles/${a.slug}.html" class="card-link">
        <div class="card-img-wrap">
          <img src="${a.cardImage}" alt="${a.title}" class="card-img" loading="lazy">
          <span class="card-tag">${a.categoryLabel}</span>
        </div>
        <div class="card-body">
          <span class="card-num">${n}</span>
          <h3 class="card-title">${a.title}</h3>
          <p class="card-excerpt">${a.excerpt}</p>
          <div class="card-meta">
            <span class="card-author">${a.author.name}</span>
            <span class="card-date">${a.dateFormatted}</span>
            <span class="card-read">${a.readTime}</span>
          </div>
        </div>
      </a>
    </article>`;
  }

    /* ============================================================
     LOAD MORE (placeholder animation)
     ============================================================ */
  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('loadMore');
    if (!btn) return;

    btn.addEventListener('click', () => {
      btn.querySelector('span').textContent = 'LOADING...';
      // Simulate async — in production replace with actual fetch
      setTimeout(() => {
        btn.querySelector('span').textContent = 'MORE COLUMNS';
      }, 1500);
    });
  });

})();
