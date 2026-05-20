/**
 * AI 日报 V2 — 前端交互逻辑
 * 支持：分类筛选、排序切换、混合布局、星级评分、展开/收起、学习4板块、中英切换
 */

// ─── 全局状态 ──────────────────────────────────────────────────────────────────

let currentData = null;
let currentCategory = 'all';
let currentSort = 'importance';

// V2 分类体系（与 config.py NEWS_CATEGORIES 对齐）
const CATEGORIES = {
  'all':               { name: '全部',       icon: '📋', color: '#4F46E5' },
  'foundation-model':  { name: '大模型',     icon: '🏢', color: '#2563EB' },
  'business':          { name: '融资商业',   icon: '💰', color: '#EA580C' },
  'tech-breakthrough': { name: '技术突破',   icon: '🔬', color: '#7C3AED' },
  'product':           { name: '产品应用',   icon: '🛠️', color: '#16A34A' },
  'policy':            { name: '政策监管',   icon: '🏛️', color: '#DC2626' },
  'opinion':           { name: '行业观点',   icon: '🌐', color: '#6B7280' },
};

// 分类占位图背景色（用于没有 cover_image 时的渐变背景）
const CATEGORY_GRADIENTS = {
  'foundation-model':  ['#2563EB', '#3B82F6'],
  'business':          ['#EA580C', '#F97316'],
  'tech-breakthrough': ['#7C3AED', '#8B5CF6'],
  'product':           ['#16A34A', '#22C55E'],
  'policy':            ['#DC2626', '#EF4444'],
  'opinion':           ['#4B5563', '#6B7280'],
};

// ─── 初始化 ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  renderCategoryTabs();
  initSortSelector();
  await initDateSelector();
  const date = getUrlDate() || getLatestDate();
  await loadReport(date);
});

// ─── 日期工具 ─────────────────────────────────────────────────────────────────

function getUrlDate() {
  const params = new URLSearchParams(window.location.search);
  return params.get('date');
}

function getLatestDate() {
  const sel = document.getElementById('date-selector');
  return sel.options.length > 0 ? sel.options[0].value : formatDate(new Date());
}

function formatDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatDateCN(dateStr) {
  const [y, m, d] = dateStr.split('-');
  return `${y}年${parseInt(m)}月${parseInt(d)}日`;
}

async function initDateSelector() {
  const sel = document.getElementById('date-selector');
  const dates = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    dates.push(formatDate(d));
  }
  dates.forEach((date, idx) => {
    const opt = document.createElement('option');
    opt.value = date;
    opt.textContent = idx === 0 ? `今天 ${date}` : date;
    sel.appendChild(opt);
  });
  sel.addEventListener('change', (e) => loadReport(e.target.value));
}

// ─── 排序 ─────────────────────────────────────────────────────────────────────

function initSortSelector() {
  const sel = document.getElementById('sort-selector');
  if (!sel) return;
  sel.addEventListener('change', (e) => {
    currentSort = e.target.value;
    if (currentData) renderAll(currentData);
  });
}

// ─── 分类标签栏 ────────────────────────────────────────────────────────────────

function renderCategoryTabs() {
  const container = document.getElementById('category-tabs');
  if (!container) return;

  Object.entries(CATEGORIES).forEach(([key, cat]) => {
    const tab = document.createElement('button');
    tab.className = `cat-tab ${key === 'all' ? 'active' : ''}`;
    tab.dataset.category = key;
    tab.textContent = `${cat.icon} ${cat.name}`;
    tab.addEventListener('click', () => {
      currentCategory = key;
      document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      if (currentData) renderAll(currentData);
    });
    container.appendChild(tab);
  });
}

// ─── 数据加载 ─────────────────────────────────────────────────────────────────

async function loadReport(date) {
  try {
    let data = null;
    try {
      const res = await fetch(`data/${date}.json`);
      if (res.ok) data = await res.json();
    } catch (e) {}

    if (!data) {
      const res = await fetch('data/mock.json');
      if (res.ok) data = await res.json();
    }

    if (!data) {
      showError('暂无当日数据');
      return;
    }

    currentData = data;
    renderAll(data);

    const sel = document.getElementById('date-selector');
    if (sel.value !== date) sel.value = date;
  } catch (e) {
    showError('加载数据失败：' + e.message);
  }
}

// ─── 统一渲染入口 ─────────────────────────────────────────────────────────────

function renderAll(data) {
  updateHeader(data);
  renderNews(data.news || []);
  renderDeals(data.deals || []);
  renderLearning(data.learning || {});
}

function updateHeader(data) {
  const date = data.date || formatDate(new Date());
  document.getElementById('report-date').textContent = `${formatDateCN(date)} AI 日报`;
  const genTime = data.generated_at
    ? new Date(data.generated_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : '08:00';
  document.getElementById('report-time').textContent = `更新于 ${genTime}`;
}

// ─── 新闻筛选 & 排序 ─────────────────────────────────────────────────────────

function getFilteredNews(news) {
  // 1. 分类筛选
  let filtered = currentCategory === 'all'
    ? news
    : news.filter(n => n.category === currentCategory);

  // 2. 排序
  if (currentSort === 'importance') {
    filtered.sort((a, b) => (b.importance || 3) - (a.importance || 3));
  } else {
    filtered.sort((a, b) => new Date(b.publish_time || 0) - new Date(a.publish_time || 0));
  }

  return filtered;
}

// ─── 新闻渲染 — 混合布局 ──────────────────────────────────────────────────────

function renderNews(news) {
  const filtered = getFilteredNews(news);
  const headlineEl = document.getElementById('headline-card');
  const listEl = document.getElementById('news-list');
  document.getElementById('news-count').textContent = `${filtered.length} 条`;

  if (filtered.length === 0) {
    headlineEl.innerHTML = '';
    listEl.innerHTML = '<div class="text-gray-400 text-sm py-8 text-center">该分类暂无新闻</div>';
    return;
  }

  // 头条：取 importance 最高且有封面图的第一条，否则取第一条
  const headline = filtered.find(n => n.cover_image) || filtered[0];
  const rest = filtered.filter(n => n.id !== headline.id);

  // 渲染头条大图
  headlineEl.innerHTML = renderHeadlineCard(headline);

  // 渲染其余卡片：有封面图的用图文卡片，没有的用纯文字卡片
  listEl.innerHTML = rest.map(item => {
    return item.cover_image ? renderNewsCardWithImage(item) : renderNewsCardText(item);
  }).join('');
}

function renderHeadlineCard(item) {
  const stars = renderStars(item.importance || 5);
  const catInfo = CATEGORIES[item.category] || CATEGORIES['all'];
  const timeAgo = formatTimeAgo(item.publish_time);
  const tagHtml = (item.tags || []).slice(0, 3).map(t =>
    `<span class="bg-blue-50 text-blue-600 text-xs px-2 py-0.5 rounded">${t}</span>`
  ).join('');

  // 封面图：有图用图，没图用分类渐变占位
  const [gradFrom, gradTo] = CATEGORY_GRADIENTS[item.category] || ['#4F46E5', '#6366F1'];
  const coverHtml = item.cover_image
    ? `<div class="md:w-1/2 h-56 md:h-auto bg-gray-100 overflow-hidden">
        <img src="${item.cover_image}" alt="" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
             onerror="this.parentElement.innerHTML='<div class=\\'cover-placeholder\\' style=\\'background:linear-gradient(135deg,${gradFrom},${gradTo})\\'><span class=\\'placeholder-icon\\'>${catInfo.icon}</span></div>'">
      </div>`
    : `<div class="md:w-1/2 h-56 md:h-auto overflow-hidden">
        <div class="cover-placeholder h-full" style="background:linear-gradient(135deg,${gradFrom},${gradTo})">
          <span class="placeholder-icon">${catInfo.icon}</span>
        </div>
      </div>`;

  return `
    <article class="bg-white rounded-xl shadow-card overflow-hidden card-hover cursor-pointer group"
             onclick="window.open('${item.source_url}', '_blank')">
      <div class="md:flex">
        ${coverHtml}
        <div class="${item.cover_image ? 'md:w-1/2' : 'md:w-1/2'} p-6 flex flex-col justify-center">
          <div class="flex items-center gap-2 mb-3">
            <span class="text-xs font-medium px-2 py-0.5 rounded-full text-white" style="background:${catInfo.color}">${catInfo.name}</span>
            <span class="text-xs text-gray-400">${item.source}</span>
            ${item.language === 'en' ? '<span class="text-xs text-gray-400 font-normal">[EN]</span>' : ''}
          </div>
          <h2 class="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors leading-snug mb-3">${item.title}</h2>
          ${renderSummaryWithToggle(item)}
          <div class="flex items-center gap-3 mt-auto pt-3 flex-wrap">
            ${tagHtml}
            <span class="text-xs text-gray-400">${timeAgo}</span>
            <span class="ml-auto">${stars}</span>
          </div>
        </div>
      </div>
    </article>
  `;
}

function renderNewsCardWithImage(item) {
  const catInfo = CATEGORIES[item.category] || CATEGORIES['all'];
  const timeAgo = formatTimeAgo(item.publish_time);
  const stars = renderStars(item.importance || 3);
  const tagHtml = (item.tags || []).slice(0, 2).map(t =>
    `<span class="bg-blue-50 text-blue-600 text-xs px-2 py-0.5 rounded">${t}</span>`
  ).join('');

  // 封面图占位
  const [gradFrom, gradTo] = CATEGORY_GRADIENTS[item.category] || ['#4F46E5', '#6366F1'];
  const coverHtml = item.cover_image
    ? `<div class="h-40 bg-gray-100 overflow-hidden">
        <img src="${item.cover_image}" alt="" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
             onerror="this.parentElement.innerHTML='<div class=\\'cover-placeholder h-full\\' style=\\'background:linear-gradient(135deg,${gradFrom},${gradTo})\\'><span class=\\'placeholder-icon\\'>${catInfo.icon}</span></div>'">
      </div>`
    : `<div class="h-40 overflow-hidden">
        <div class="cover-placeholder h-full" style="background:linear-gradient(135deg,${gradFrom},${gradTo})">
          <span class="placeholder-icon">${catInfo.icon}</span>
        </div>
      </div>`;

  return `
    <article class="news-card-border bg-white rounded-lg shadow-card overflow-hidden card-hover cursor-pointer group"
             data-category="${item.category || 'all'}"
             onclick="window.open('${item.source_url}', '_blank')">
      ${coverHtml}
      <div class="p-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs font-medium px-1.5 py-0.5 rounded-full text-white" style="background:${catInfo.color}; font-size:10px">${catInfo.name}</span>
          <span class="text-xs text-gray-400">${item.source}</span>
          ${item.language === 'en' ? '<span class="text-xs text-gray-400">[EN]</span>' : ''}
        </div>
        <h3 class="text-sm font-semibold text-gray-900 group-hover:text-blue-600 transition-colors leading-snug mb-2 line-clamp-2">${item.title}</h3>
        ${renderSummaryWithToggle(item)}
        <div class="flex items-center gap-2 mt-2 flex-wrap">
          ${tagHtml}
          <span class="text-xs text-gray-400">${timeAgo}</span>
          <span class="ml-auto">${stars}</span>
        </div>
      </div>
    </article>
  `;
}

function renderNewsCardText(item) {
  const catInfo = CATEGORIES[item.category] || CATEGORIES['all'];
  const timeAgo = formatTimeAgo(item.publish_time);
  const stars = renderStars(item.importance || 3);
  const tagHtml = (item.tags || []).slice(0, 3).map(t =>
    `<span class="bg-blue-50 text-blue-600 text-xs px-2 py-0.5 rounded">${t}</span>`
  ).join('');

  return `
    <article class="news-card-border bg-white rounded-lg shadow-card p-5 card-hover cursor-pointer group"
             data-category="${item.category || 'all'}"
             onclick="window.open('${item.source_url}', '_blank')">
      <div class="flex items-start justify-between gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs font-medium px-1.5 py-0.5 rounded-full text-white" style="background:${catInfo.color}; font-size:10px">${catInfo.name}</span>
            <span class="text-xs text-gray-400">${item.source}</span>
            ${item.language === 'en' ? '<span class="text-xs text-gray-400">[EN]</span>' : ''}
          </div>
          <h3 class="text-base font-semibold text-gray-900 group-hover:text-blue-600 transition-colors leading-snug mb-2">${item.title}</h3>
          ${renderSummaryWithToggle(item)}
          <div class="flex items-center gap-3 flex-wrap mt-1">
            ${tagHtml}
            <span class="text-xs text-gray-400">${timeAgo}</span>
          </div>
        </div>
        <div class="flex flex-col items-end gap-1 flex-shrink-0">
          <span class="text-gray-300 group-hover:text-blue-400 transition-colors">↗</span>
          ${stars}
        </div>
      </div>
    </article>
  `;
}

// ─── 摘要 + 翻译切换 ──────────────────────────────────────────────────────────

function renderSummaryWithToggle(item) {
  const hasTranslation = item.language === 'en' && item.summary_translated;
  if (!item.summary) return '';

  if (hasTranslation) {
    return `
      <div class="text-sm text-gray-600 leading-relaxed mb-1" id="summary-${item.id}">
        ${item.summary_translated}
      </div>
      <button onclick="event.stopPropagation(); toggleTranslation('${item.id}', ${JSON.stringify(item.summary)}, ${JSON.stringify(item.summary_translated)})"
        class="text-xs text-blue-500 hover:text-blue-700 mb-1" id="toggle-btn-${item.id}">查看原文 →</button>
    `;
  }
  return `<p class="text-sm text-gray-600 leading-relaxed mb-1 line-clamp-3">${item.summary}</p>`;
}

function toggleTranslation(id, original, translated) {
  const el = document.getElementById(`summary-${id}`);
  const btn = document.getElementById(`toggle-btn-${id}`);
  if (!el || !btn) return;
  const isShowingTranslation = btn.textContent.includes('查看原文');
  if (isShowingTranslation) {
    el.textContent = original;
    btn.textContent = '查看翻译 →';
  } else {
    el.textContent = translated;
    btn.textContent = '查看原文 →';
  }
}

// ─── 星级渲染 ─────────────────────────────────────────────────────────────────

function renderStars(importance) {
  const max = 5;
  let html = '';
  for (let i = 1; i <= max; i++) {
    html += `<span class="star ${i <= importance ? 'filled' : ''}">★</span>`;
  }
  return `<span class="text-xs">${html}</span>`;
}

// ─── 投融资渲染 ────────────────────────────────────────────────────────────────

function renderDeals(deals) {
  const container = document.getElementById('deals-list');
  document.getElementById('deals-count').textContent = `${deals.length} 条`;

  if (deals.length === 0) {
    container.innerHTML = '<div class="text-gray-400 text-sm py-8 text-center col-span-3">暂无投融资数据</div>';
    return;
  }

  container.innerHTML = deals.map(item => renderDealCard(item)).join('');
}

function renderDealCard(item) {
  const tagHtml = (item.industry_tags || []).slice(0, 2).map(t =>
    `<span class="bg-green-50 text-green-600 text-xs px-1.5 py-0.5 rounded">${t}</span>`
  ).join('');
  const investors = (item.investors || []).join('、');
  const hasDetailPage = item.detail_url;

  return `
    <article class="bg-white rounded-lg shadow-card p-4 card-hover cursor-pointer group ${hasDetailPage ? '' : ''}"
             onclick="${hasDetailPage ? `window.open('${item.detail_url}', '_blank')` : item.source_url ? `window.open('${item.source_url}', '_blank')` : ''}">
      <div class="flex items-start justify-between mb-2">
        <div>
          <h3 class="font-bold text-gray-900 group-hover:text-blue-600 transition-colors">${item.company}</h3>
          ${item.company_en ? `<p class="text-xs text-gray-400">${item.company_en}</p>` : ''}
        </div>
        <span class="text-xs font-medium bg-blue-50 text-blue-600 px-2 py-1 rounded flex-shrink-0">${item.round}</span>
      </div>
      <p class="text-xl font-bold text-gray-900 mb-2">${item.amount}</p>
      ${item.company_intro ? `<p class="text-xs text-gray-500 leading-relaxed mb-2 line-clamp-2">${item.company_intro}</p>` : ''}
      ${investors ? `<p class="text-xs text-gray-500 mb-2">投资方：${investors}</p>` : ''}
      ${item.description ? `<p class="text-xs text-gray-400 leading-relaxed mb-2 line-clamp-2">${item.description}</p>` : ''}
      <div class="flex gap-1 flex-wrap">${tagHtml}</div>
    </article>
  `;
}

// ─── 学习内容渲染 — 4 板块 ────────────────────────────────────────────────────

function renderLearning(learning) {
  // V2: learning 是 dict，包含 concepts / deep_reads / videos / daily_question
  // 兼容 V1: learning 可能是平铺数组
  let concepts, deepReads, videos, dailyQuestion;
  if (Array.isArray(learning)) {
    // V1 兼容：把旧格式转成新格式
    concepts = learning;
    deepReads = [];
    videos = [];
    dailyQuestion = {};
  } else {
    concepts = learning.concepts || [];
    deepReads = learning.deep_reads || [];
    videos = learning.videos || [];
    dailyQuestion = learning.daily_question || {};
  }

  // 计算学习时间
  let totalMin = 0;
  concepts.forEach(c => { totalMin += (c.recommended_reading?.reading_time || 5); });
  deepReads.forEach(r => { totalMin += (r.reading_time || 8); });
  videos.forEach(v => { totalMin += parseInt(v.duration) || 10; });
  totalMin += 5; // 每日一问
  document.getElementById('learning-time').textContent = `预计学习：${totalMin || 35} 分钟`;

  // 📌 核心概念
  const conceptsEl = document.getElementById('concepts-list');
  conceptsEl.innerHTML = concepts.length > 0
    ? concepts.map(c => renderConceptCard(c)).join('')
    : '<div class="text-gray-400 text-sm py-4 text-center">暂无概念</div>';

  // 📰 深度阅读
  const deepReadsEl = document.getElementById('deep-reads-list');
  deepReadsEl.innerHTML = deepReads.length > 0
    ? deepReads.map(r => renderDeepReadCard(r)).join('')
    : '<div class="text-gray-400 text-sm py-4 text-center">暂无深度阅读</div>';

  // 🎬 视频学习
  const videosEl = document.getElementById('videos-list');
  videosEl.innerHTML = videos.length > 0
    ? videos.map(v => renderVideoCard(v)).join('')
    : '<div class="text-gray-400 text-sm py-4 text-center">暂无视频推荐</div>';

  // 💡 每日一问
  const questionEl = document.getElementById('daily-question');
  if (dailyQuestion.question) {
    questionEl.innerHTML = renderDailyQuestion(dailyQuestion);
  } else {
    questionEl.innerHTML = '<div class="text-gray-400 text-sm py-4 text-center">暂无每日一问</div>';
  }
}

function renderConceptCard(item) {
  const diffMap = {
    beginner:     ['入门', 'difficulty-beginner'],
    intermediate: ['进阶', 'difficulty-intermediate'],
    advanced:     ['高阶', 'difficulty-advanced'],
  };
  const [diffLabel, diffClass] = diffMap[item.difficulty] || ['入门', 'difficulty-beginner'];

  const readingHtml = item.recommended_reading ? `
    <a href="${item.recommended_reading.url}" target="_blank" class="flex items-center gap-2 text-xs text-blue-600 hover:underline">
      <span>📄</span>
      <span>${item.recommended_reading.title}</span>
      <span class="text-gray-400">(约 ${item.recommended_reading.reading_time} 分钟)</span>
    </a>
  ` : '';

  const videoHtml = item.recommended_video ? `
    <a href="${item.recommended_video.url}" target="_blank" class="flex items-center gap-2 text-xs text-red-500 hover:underline">
      <span>${item.recommended_video.platform === 'bilibili' ? '📺' : '▶️'}</span>
      <span>${item.recommended_video.title}</span>
      <span class="text-gray-400">(${item.recommended_video.duration})</span>
    </a>
  ` : '';

  return `
    <div class="bg-white rounded-lg shadow-card overflow-hidden">
      <div class="p-5 cursor-pointer" onclick="toggleLearnCard('${item.id}')">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <span class="tag-dot ${diffClass}"></span>
              <h3 class="font-bold text-gray-900">${item.concept}</h3>
              <span class="text-xs text-gray-400">${item.concept_en}</span>
              <span class="text-xs text-gray-500 ${diffClass} px-1.5 py-0.5 rounded">${diffLabel}</span>
            </div>
            <p class="text-sm text-gray-600 leading-relaxed">${item.definition}</p>
          </div>
          <span id="learn-icon-${item.id}" class="text-gray-400 flex-shrink-0 mt-1 transition-transform duration-200">▼</span>
        </div>
      </div>
      <div id="learn-detail-${item.id}" class="expand-content">
        <div class="border-t border-gray-100 px-5 py-4 space-y-4">
          <div>
            <p class="text-xs font-medium text-gray-500 mb-1">💡 通俗解释</p>
            <p class="text-sm text-gray-700 leading-relaxed">${item.explanation}</p>
          </div>
          <div>
            <p class="text-xs font-medium text-gray-500 mb-1">🎯 应用场景</p>
            <p class="text-sm text-gray-700 leading-relaxed">${item.example}</p>
          </div>
          ${readingHtml || videoHtml ? `
          <div>
            <p class="text-xs font-medium text-gray-500 mb-2">📖 推荐学习</p>
            <div class="space-y-1.5">${readingHtml}${videoHtml}</div>
          </div>
          ` : ''}
        </div>
      </div>
    </div>
  `;
}

function renderDeepReadCard(item) {
  const mustReadBadge = item.is_must_read
    ? '<span class="text-xs bg-red-50 text-red-500 px-1.5 py-0.5 rounded font-medium">必读</span>'
    : '';

  return `
    <a href="${item.url}" target="_blank" class="block bg-white rounded-lg shadow-card p-5 card-hover group">
      <div class="flex items-start justify-between gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-2">
            ${mustReadBadge}
            <span class="text-xs text-gray-400">${item.source} · 约 ${item.reading_time} 分钟</span>
          </div>
          <h3 class="text-base font-semibold text-gray-900 group-hover:text-blue-600 transition-colors leading-snug mb-2">${item.title}</h3>
          <p class="text-sm text-gray-600 leading-relaxed line-clamp-3">${item.ai_summary}</p>
        </div>
        <span class="text-gray-300 group-hover:text-blue-400 transition-colors flex-shrink-0 mt-1">↗</span>
      </div>
    </a>
  `;
}

function renderVideoCard(item) {
  const platformIcon = item.platform === 'bilibili' ? '📺' : '▶️';
  const platformName = item.platform === 'bilibili' ? 'B站' : 'YouTube';

  return `
    <a href="${item.url}" target="_blank" class="block bg-white rounded-lg shadow-card p-4 card-hover group">
      <div class="flex items-center gap-3">
        <span class="text-2xl">${platformIcon}</span>
        <div class="flex-1 min-w-0">
          <h3 class="text-sm font-semibold text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-1">${item.title}</h3>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-xs text-gray-400">${platformName} · ${item.duration}</span>
          </div>
          ${item.ai_summary ? `<p class="text-xs text-gray-500 mt-1 line-clamp-2">${item.ai_summary}</p>` : ''}
        </div>
        <span class="text-gray-300 group-hover:text-blue-400 transition-colors flex-shrink-0">↗</span>
      </div>
    </a>
  `;
}

function renderDailyQuestion(item) {
  const relatedHtml = (item.related_concepts || []).map(c =>
    `<span class="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">${c}</span>`
  ).join('');

  return `
    <div class="bg-white rounded-lg shadow-card overflow-hidden">
      <div class="p-5 cursor-pointer" onclick="toggleDailyQuestion()">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-lg">💡</span>
              <h3 class="font-bold text-gray-900">${item.question}</h3>
            </div>
            <div class="flex gap-1 flex-wrap">${relatedHtml}</div>
          </div>
          <span id="question-icon" class="text-gray-400 flex-shrink-0 mt-1 transition-transform duration-200">▼</span>
        </div>
      </div>
      <div id="question-detail" class="expand-content">
        <div class="border-t border-gray-100 px-5 py-4">
          <p class="text-sm text-gray-700 leading-relaxed">${item.answer}</p>
        </div>
      </div>
    </div>
  `;
}

// ─── 展开 / 收起 ──────────────────────────────────────────────────────────────

function toggleLearnCard(id) {
  const detail = document.getElementById(`learn-detail-${id}`);
  const icon = document.getElementById(`learn-icon-${id}`);
  if (!detail || !icon) return;
  const isOpen = detail.classList.contains('open');
  detail.classList.toggle('open', !isOpen);
  icon.style.transform = isOpen ? '' : 'rotate(180deg)';
}

function toggleDailyQuestion() {
  const detail = document.getElementById('question-detail');
  const icon = document.getElementById('question-icon');
  if (!detail || !icon) return;
  const isOpen = detail.classList.contains('open');
  detail.classList.toggle('open', !isOpen);
  icon.style.transform = isOpen ? '' : 'rotate(180deg)';
}

// ─── 工具函数 ─────────────────────────────────────────────────────────────────

function formatTimeAgo(timeStr) {
  if (!timeStr) return '';
  const now = new Date();
  const then = new Date(timeStr);
  if (isNaN(then.getTime())) return '';
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  if (diffMin < 60) return `${diffMin} 分钟前`;
  if (diffHour < 24) return `${diffHour} 小时前`;
  if (diffDay < 7) return `${diffDay} 天前`;
  return then.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

function showError(msg) {
  ['headline-card', 'news-list', 'deals-list', 'concepts-list', 'deep-reads-list', 'videos-list', 'daily-question'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<div class="text-gray-400 text-sm py-8 text-center">${msg}</div>`;
  });
}
