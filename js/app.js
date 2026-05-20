// AI 日报前端交互逻辑
// 支持：日期切换、新闻/投融资展开收起、中英切换、学习卡片展开

let currentData = null;
let newsShowAll = false;
let dealsShowAll = false;
const NEWS_PREVIEW_COUNT = 5;
const DEALS_PREVIEW_COUNT = 3;

// ─── 初始化 ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
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
  // 尝试从 data/ 目录获取可用日期列表
  // GitHub Pages 环境下通过约定文件获取；本地用 mock
  const sel = document.getElementById('date-selector');

  // 生成最近 7 天的选项（实际部署时可从 index.json 读取）
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

  sel.addEventListener('change', (e) => {
    loadReport(e.target.value);
  });
}

// ─── 数据加载 ─────────────────────────────────────────────────────────────────

async function loadReport(date) {
  try {
    // 先尝试加载对应日期的 JSON，失败则 fallback 到 mock
    let data = null;
    try {
      const res = await fetch(`data/${date}.json`);
      if (res.ok) data = await res.json();
    } catch (e) {}

    if (!data) {
      // fallback: 加载 mock 数据
      const res = await fetch('data/mock.json');
      if (res.ok) data = await res.json();
    }

    if (!data) {
      showError('暂无当日数据');
      return;
    }

    currentData = data;
    newsShowAll = false;
    dealsShowAll = false;
    renderReport(data, date);

    // 同步日期选择器
    const sel = document.getElementById('date-selector');
    if (sel.value !== date) sel.value = date;
  } catch (e) {
    showError('加载数据失败：' + e.message);
  }
}

// ─── 渲染入口 ─────────────────────────────────────────────────────────────────

function renderReport(data, date) {
  updateHeader(data, date);
  renderNews(data.news || []);
  renderDeals(data.deals || []);
  renderLearning(data.learning || []);
}

function updateHeader(data, date) {
  document.getElementById('report-date').textContent = `${formatDateCN(date)} AI 日报`;
  const genTime = data.generated_at ? new Date(data.generated_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : '08:00';
  document.getElementById('report-time').textContent = `更新于 ${genTime}`;

  // 计算学习时间
  const totalMin = (data.learning || []).reduce((sum, item) => {
    return sum + (item.articles || []).reduce((s, a) => s + (a.reading_time || 5), 0);
  }, 0) + (data.learning || []).length * 3;
  document.getElementById('reading-time').textContent = `约 ${totalMin || 15} 分钟`;
}

// ─── 新闻渲染 ─────────────────────────────────────────────────────────────────

function renderNews(news) {
  const container = document.getElementById('news-list');
  document.getElementById('news-count').textContent = `${news.length} 条`;

  const items = newsShowAll ? news : news.slice(0, NEWS_PREVIEW_COUNT);
  container.innerHTML = items.map(item => renderNewsCard(item)).join('');
}

function renderNewsCard(item) {
  const timeAgo = formatTimeAgo(item.publish_time);
  const hasTranslation = item.language === 'en' && item.summary_translated;
  const tagHtml = (item.tags || []).slice(0, 3).map(t =>
    `<span class="bg-blue-50 text-blue-600 text-xs px-2 py-0.5 rounded">${t}</span>`
  ).join('');

  return `
    <article class="bg-white rounded-lg shadow-sm p-5 card-hover cursor-pointer group" onclick="window.open('${item.source_url}', '_blank')">
      <div class="flex items-start justify-between gap-3">
        <div class="flex-1 min-w-0">
          <h3 class="text-base font-semibold text-gray-900 group-hover:text-blue-600 transition-colors leading-snug mb-2">
            ${item.title}
            ${item.language === 'en' ? '<span class="ml-1 text-xs text-gray-400 font-normal">[EN]</span>' : ''}
          </h3>
          ${hasTranslation ? `
            <div class="text-sm text-gray-600 leading-relaxed mb-2" id="summary-${item.id}">
              ${item.summary_translated}
            </div>
            <button onclick="event.stopPropagation(); toggleTranslation('${item.id}', \`${item.summary}\`, \`${item.summary_translated}\`)"
              class="text-xs text-blue-500 hover:text-blue-700 mb-2" id="toggle-btn-${item.id}">查看原文 →</button>
          ` : `
            <p class="text-sm text-gray-600 leading-relaxed mb-2">${item.summary}</p>
          `}
          <div class="flex items-center gap-3 flex-wrap">
            ${tagHtml}
            <span class="text-xs text-gray-400">${item.source} · ${timeAgo}</span>
          </div>
        </div>
        <span class="text-gray-300 group-hover:text-blue-400 transition-colors flex-shrink-0 mt-1">↗</span>
      </div>
    </article>
  `;
}

function toggleNewsAll() {
  newsShowAll = !newsShowAll;
  renderNews(currentData.news || []);
  const btn = document.getElementById('news-expand-btn');
  const icon = document.getElementById('news-expand-icon');
  btn.querySelector('span:first-child') && (btn.childNodes[0].textContent = newsShowAll ? '收起 ' : '查看全部 ');
  icon.textContent = newsShowAll ? '↑' : '→';
}

function toggleTranslation(id, original, translated) {
  const el = document.getElementById(`summary-${id}`);
  const btn = document.getElementById(`toggle-btn-${id}`);
  const isShowingTranslation = btn.textContent.includes('查看原文');
  if (isShowingTranslation) {
    el.textContent = original;
    btn.textContent = '查看翻译 →';
  } else {
    el.textContent = translated;
    btn.textContent = '查看原文 →';
  }
}

// ─── 投融资渲染 ───────────────────────────────────────────────────────────────

function renderDeals(deals) {
  const container = document.getElementById('deals-list');
  document.getElementById('deals-count').textContent = `${deals.length} 条`;

  const items = dealsShowAll ? deals : deals.slice(0, DEALS_PREVIEW_COUNT);
  container.innerHTML = items.map(item => renderDealCard(item)).join('');
}

function renderDealCard(item) {
  const tagHtml = (item.industry_tags || []).slice(0, 2).map(t =>
    `<span class="bg-green-50 text-green-600 text-xs px-1.5 py-0.5 rounded">${t}</span>`
  ).join('');
  const investors = (item.investors || []).join('、');

  return `
    <article class="bg-white rounded-lg shadow-sm p-4 card-hover cursor-pointer group" onclick="window.open('${item.source_url}', '_blank')">
      <div class="flex items-start justify-between mb-2">
        <div>
          <h3 class="font-bold text-gray-900 group-hover:text-blue-600 transition-colors">${item.company}</h3>
          ${item.company_en ? `<p class="text-xs text-gray-400">${item.company_en}</p>` : ''}
        </div>
        <span class="text-xs font-medium bg-blue-50 text-blue-600 px-2 py-1 rounded flex-shrink-0">${item.round}</span>
      </div>
      <p class="text-xl font-bold text-gray-900 mb-2">${item.amount}</p>
      ${investors ? `<p class="text-xs text-gray-500 mb-3">投资方：${investors}</p>` : ''}
      <p class="text-xs text-gray-500 leading-relaxed mb-2">${item.description}</p>
      <div class="flex gap-1 flex-wrap">${tagHtml}</div>
    </article>
  `;
}

function toggleDealsAll() {
  dealsShowAll = !dealsShowAll;
  renderDeals(currentData.deals || []);
  const icon = document.getElementById('deals-expand-icon');
  icon.textContent = dealsShowAll ? '↑' : '→';
}

// ─── 学习卡片渲染 ─────────────────────────────────────────────────────────────

function renderLearning(items) {
  const container = document.getElementById('learning-list');
  const totalMin = items.reduce((sum, item) => {
    return sum + (item.articles || []).reduce((s, a) => s + (a.reading_time || 5), 0) + 3;
  }, 0);
  document.getElementById('learning-time').textContent = `预计学习时间：${totalMin || 15} 分钟`;

  container.innerHTML = items.map(item => renderLearnCard(item)).join('');
}

function renderLearnCard(item) {
  const diffMap = { beginner: ['入门', 'difficulty-beginner'], intermediate: ['进阶', 'difficulty-intermediate'], advanced: ['高阶', 'difficulty-advanced'] };
  const [diffLabel, diffClass] = diffMap[item.difficulty] || ['入门', 'difficulty-beginner'];

  const articlesHtml = (item.articles || []).map(a => `
    <a href="${a.url}" target="_blank" class="flex items-center gap-2 text-xs text-blue-600 hover:underline">
      <span>${a.language === 'zh' ? '📄' : '🌐'}</span>
      <span>${a.title}</span>
      <span class="text-gray-400">(约 ${a.reading_time} 分钟)</span>
    </a>
  `).join('');

  const videoHtml = item.video ? `
    <a href="${item.video.url}" target="_blank" class="flex items-center gap-2 text-xs text-red-500 hover:underline">
      <span>${item.video.platform === 'bilibili' ? '📺' : '▶️'}</span>
      <span>${item.video.title}</span>
      <span class="text-gray-400">(${item.video.duration})</span>
    </a>
  ` : '';

  return `
    <div class="bg-white rounded-lg shadow-sm overflow-hidden">
      <div class="p-5 cursor-pointer" onclick="toggleLearnCard('${item.id}')">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <span class="tag-dot ${diffClass}"></span>
              <h3 class="font-bold text-gray-900">${item.concept}</h3>
              <span class="text-xs text-gray-400">${item.concept_en}</span>
              <span class="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">${diffLabel}</span>
            </div>
            <p class="text-sm text-gray-600 leading-relaxed">${item.definition}</p>
          </div>
          <span id="learn-icon-${item.id}" class="text-gray-400 flex-shrink-0 mt-1 transition-transform">▼</span>
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
          ${articlesHtml || videoHtml ? `
          <div>
            <p class="text-xs font-medium text-gray-500 mb-2">📖 推荐阅读</p>
            <div class="space-y-1.5">${articlesHtml}${videoHtml}</div>
          </div>
          ` : ''}
        </div>
      </div>
    </div>
  `;
}

function toggleLearnCard(id) {
  const detail = document.getElementById(`learn-detail-${id}`);
  const icon = document.getElementById(`learn-icon-${id}`);
  const isOpen = detail.classList.contains('open');
  detail.classList.toggle('open', !isOpen);
  icon.style.transform = isOpen ? '' : 'rotate(180deg)';
}

// ─── 工具函数 ─────────────────────────────────────────────────────────────────

function formatTimeAgo(timeStr) {
  if (!timeStr) return '';
  const now = new Date();
  const then = new Date(timeStr);
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
  ['news-list', 'deals-list', 'learning-list'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<div class="text-gray-400 text-sm py-8 text-center">${msg}</div>`;
  });
}
