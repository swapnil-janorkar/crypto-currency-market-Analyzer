const API_ROOT = '';

const state = {
  liveData: [],
  selectedCoin: null,
  chart: null,
};

const formatCurrency = (value) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value || 0);

const formatCompact = (value) =>
  new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(value || 0);

const fetchJSON = async (path) => {
  const response = await fetch(`${API_ROOT}${path}`);
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || 'Request failed');
  }
  return response.json();
};

const updateLiveTimestamp = () => {
  const now = new Date();
  const label = document.getElementById('live-timestamp');
  if (label) {
    label.textContent = `Updated ${now.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    })}`;
  }
};

const displayName = (slug) =>
  slug
    .split('-')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');

const createLiveCard = (coinData) => {
  const wrapper = document.createElement('article');
  wrapper.className = 'live-card';
  const change = coinData.change_percentage_24h ?? 0;
  const changeSign = change >= 0 ? '+' : '';
  wrapper.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <strong>${displayName(coinData.coin)}</strong>
      <span class='change ${change >= 0 ? 'change--positive' : 'change--negative'}'>${changeSign}${change.toFixed(2)}%</span>
    </div>
    <h3>${formatCurrency(coinData.price)}</h3>
    <p class='meta'>Volume · ${formatCompact(coinData.volume)}</p>
    <p class='meta'>Mkt cap · ${formatCompact(coinData.market_cap)}</p>
  `;
  wrapper.addEventListener('click', () => {
    state.selectedCoin = coinData.coin;
    const selector = document.getElementById('coin-select');
    selector.value = coinData.coin;
    loadCoinDetails(coinData.coin);
    document.getElementById('coin-title').textContent = coinData.coin.toUpperCase();
  });
  return wrapper;
};

const populateLiveCards = (coins) => {
  const container = document.getElementById('live-cards');
  container.innerHTML = '';
  coins
    .sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0))
    .slice(0, 6)
    .forEach((coin) => container.appendChild(createLiveCard(coin)));
};

const populateCoinSelector = (coins) => {
  const select = document.getElementById('coin-select');
  select.innerHTML = '';
  coins.forEach((coin) => {
    const option = document.createElement('option');
    option.value = coin.coin;
    option.textContent = coin.coin.toUpperCase();
    select.appendChild(option);
  });
  if (!state.selectedCoin && coins.length) {
    state.selectedCoin = coins[0].coin;
  }
  select.value = state.selectedCoin || '';
};

const updatePredictionPanel = (data) => {
  if (!data) return;
  const priceEl = document.getElementById('prediction-price');
  const trendEl = document.getElementById('prediction-trend');
  const changeEl = document.getElementById('prediction-change');
  const metaEl = document.getElementById('prediction-meta');
  priceEl.textContent = formatCurrency(data.predicted_price);
  const trendLabel = data.trend?.charAt(0).toUpperCase() + data.trend?.slice(1);
  trendEl.textContent = `${trendLabel} · ${data.model_name}`;
  trendEl.className = `small prediction-trend-${data.trend}`;
  const change = data.predicted_price - data.current_price;
  const changePct = data.current_price
    ? (change / data.current_price) * 100
    : 0;
  changeEl.textContent = `${change >= 0 ? '+' : ''}${changePct.toFixed(2)}% vs current`;
  metaEl.innerHTML = `
    <span>Confidence · ${(data.confidence * 100).toFixed(1)}%</span>
    <span>Target · ${new Date(data.target_time).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    })}</span>
  `;
};

const updateInsight = (text) => {
  const insightEl = document.getElementById('insight-text');
  insightEl.textContent = text || 'Insight unavailable right now.';
};

const renderDominance = (payload) => {
  const target = document.getElementById('dominance-list');
  if (!payload || !payload.labels?.length) {
    target.textContent = 'Dominance data coming soon.';
    return;
  }
  target.innerHTML = '';
  payload.labels.forEach((label, index) => {
    const row = document.createElement('div');
    row.className = 'dominance-entry';
    row.innerHTML = `
      <span>${label.toUpperCase()}</span>
      <span>${payload.dominance_pct?.[index] ?? 0}%</span>
    `;
    target.appendChild(row);
  });
};

const renderHeatmap = (payload) => {
  const heatmap = document.getElementById('heatmap');
  if (!payload || !payload.coins?.length) {
    heatmap.textContent = 'Heatmap data coming soon.';
    return;
  }
  heatmap.innerHTML = '';
  payload.coins.forEach((coin, index) => {
    const tile = document.createElement('div');
    tile.className = 'heat-tile';
    const change = payload.change_pct_7d?.[index] ?? 0;
    tile.innerHTML = `
      <strong>${coin.toUpperCase()}</strong>
      <span class="small" style="color:${change >= 0 ? 'var(--positive)' : 'var(--negative)'};">
        ${change >= 0 ? '+' : ''}${change.toFixed(2)}%
      </span>
    `;
    tile.style.background = change >= 0 ? 'rgba(20, 181, 142, 0.08)' : 'rgba(239, 91, 87, 0.12)';
    heatmap.appendChild(tile);
  });
};

const ensureChart = () => {
  if (state.chart) return;
  const ctx = document.getElementById('price-chart');
  state.chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: '#111827',
            boxWidth: 12,
            boxHeight: 6,
          },
        },
        tooltip: {
          mode: 'index',
          intersect: false,
        },
      },
      scales: {
        x: {
          ticks: {
            color: '#111827',
          },
          grid: {
            display: false,
          },
        },
        y: {
          ticks: {
            color: '#111827',
          },
          grid: {
            color: 'rgba(15, 23, 42, 0.08)',
          },
        },
      },
    },
  });
};

const updateChart = (payload) => {
  ensureChart();
  if (!payload || !payload.labels?.length) {
    state.chart.data.labels = [];
    state.chart.data.datasets = [];
    const legend = document.getElementById('chart-legend');
    legend.textContent = 'Historical data is not available yet.';
    state.chart.update();
    return;
  }

  const datasets = [
    {
      label: 'Price',
      data: payload.price || [],
      borderColor: 'var(--accent)',
      backgroundColor: 'rgba(31, 111, 235, 0.12)',
      pointRadius: 0,
      borderWidth: 2,
      tension: 0.35,
    },
  ];

  if (payload.sma_7?.length) {
    datasets.push({
      label: 'SMA 7',
      data: payload.sma_7,
      borderColor: '#9c9cff',
      borderWidth: 1.5,
      pointRadius: 0,
      borderDash: [6, 6],
      tension: 0.3,
    });
  }

  if (payload.sma_30?.length) {
    datasets.push({
      label: 'SMA 30',
      data: payload.sma_30,
      borderColor: '#8f8f9b',
      borderWidth: 1.5,
      pointRadius: 0,
      borderDash: [4, 8],
      tension: 0.3,
    });
  }

  state.chart.data.labels = payload.labels;
  state.chart.data.datasets = datasets;
  state.chart.update();

  const legend = document.getElementById('chart-legend');
  const rsi = payload.rsi?.at(-1);
  const macd = payload.macd?.at(-1);
  legend.innerHTML = `
    <span>RSI · ${rsi ? rsi.toFixed(1) : '—'}</span>
    <span>MACD · ${macd ? macd.toFixed(2) : '—'}</span>
  `;
};

const loadCoinDetails = async (coin) => {
  if (!coin) return;
  document.getElementById('coin-title').textContent = coin.toUpperCase();
  try {
    const [predRes, insightRes, vizRes] = await Promise.all([
      fetchJSON(`prediction/${coin}?model=xgboost`),
      fetchJSON(`insights/${coin}`),
      fetchJSON(`visualizations/${coin}?days=30`),
    ]);
    updatePredictionPanel(predRes.data);
    updateInsight(insightRes.insight);
    updateChart(vizRes.price_chart);
  } catch (error) {
    console.error(error);
    updateInsight('Unable to load insight right now.');
  }
};

const loadMarketPulse = async () => {
  try {
    const [dominance, heatmap] = await Promise.all([
      fetchJSON('visualizations/market/dominance'),
      fetchJSON('visualizations/market/heatmap'),
    ]);
    renderDominance(dominance.data);
    renderHeatmap(heatmap.data);
  } catch (error) {
    console.error(error);
  }
};

const refreshLiveData = async () => {
  try {
    const payload = await fetchJSON('live-data');
    state.liveData = payload.data || [];
    populateLiveCards(state.liveData);
    populateCoinSelector(state.liveData);
    if (state.selectedCoin) {
      loadCoinDetails(state.selectedCoin);
    }
    updateLiveTimestamp();
  } catch (error) {
    console.error(error);
  }
};

const init = () => {
  document.getElementById('coin-select').addEventListener('change', (event) => {
    state.selectedCoin = event.target.value;
    loadCoinDetails(state.selectedCoin);
  });
  document.getElementById('refresh-btn').addEventListener('click', refreshLiveData);
  refreshLiveData();
  loadMarketPulse();
};

document.addEventListener('DOMContentLoaded', init);
