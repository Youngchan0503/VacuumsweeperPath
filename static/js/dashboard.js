// ==========================================================================
// SeoulPark Studio - Chart.js Visualization Logic
// ==========================================================================

let barChartInstance = null;
let donutChartInstance = null;
let trendChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
  renderCharts();
});

async function renderCharts() {
  try {
    const res = await fetch('/api/analysis');
    const json = await res.json();
    if (!json.success || !json.data || !json.data.charts) return;

    const charts = json.data.charts;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#94a3b8' : '#475569';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)';

    // 1. District Bar Chart (Dual Axis: 이용률 vs 잔여석)
    const barCtx = document.getElementById('barChart');
    if (barCtx && charts.bar) {
      if (barChartInstance) barChartInstance.destroy();
      barChartInstance = new Chart(barCtx, {
        type: 'bar',
        data: {
          labels: charts.bar.labels,
          datasets: charts.bar.datasets.map(ds => ({
            ...ds,
            borderRadius: 6,
            borderSkipped: false
          }))
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: textColor, font: { family: 'Pretendard', weight: '600' } }
            },
            tooltip: {
              backgroundColor: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
              titleColor: isDark ? '#f8fafc' : '#0f172a',
              bodyColor: isDark ? '#cbd5e1' : '#334155',
              borderColor: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
              borderWidth: 1,
              padding: 10,
              cornerRadius: 8
            }
          },
          scales: {
            x: {
              grid: { color: gridColor },
              ticks: { color: textColor, font: { family: 'Pretendard' } }
            },
            y: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: '평균 이용률(%)', color: textColor },
              grid: { color: gridColor },
              ticks: { color: textColor, font: { family: 'Pretendard' } },
              max: 100
            },
            y1: {
              type: 'linear',
              position: 'right',
              title: { display: true, text: '잔여 주차면(면)', color: textColor },
              grid: { drawOnChartArea: false },
              ticks: { color: textColor, font: { family: 'Pretendard' } }
            }
          }
        }
      });
    }

    // 2. Donut Chart (혼잡도 등급 분포)
    const donutCtx = document.getElementById('donutChart');
    if (donutCtx && charts.donut) {
      if (donutChartInstance) donutChartInstance.destroy();
      donutChartInstance = new Chart(donutCtx, {
        type: 'doughnut',
        data: {
          labels: charts.donut.labels,
          datasets: charts.donut.datasets.map(ds => ({
            ...ds,
            borderWidth: 2,
            borderColor: isDark ? '#171f32' : '#ffffff'
          }))
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: textColor, font: { family: 'Pretendard', weight: '600' }, boxWidth: 12 }
            }
          },
          cutout: '68%'
        }
      });
    }

    // 3. Time Series Trend Chart (10:39 ~ 14:39)
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx && charts.trend) {
      if (trendChartInstance) trendChartInstance.destroy();
      trendChartInstance = new Chart(trendCtx, {
        type: 'line',
        data: {
          labels: charts.trend.labels,
          datasets: charts.trend.datasets.map(ds => ({
            ...ds,
            pointRadius: 2,
            pointHoverRadius: 5
          }))
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: textColor, font: { family: 'Pretendard', weight: '600' } }
            },
            tooltip: {
              backgroundColor: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
              titleColor: isDark ? '#f8fafc' : '#0f172a',
              bodyColor: isDark ? '#cbd5e1' : '#334155',
              borderWidth: 1,
              cornerRadius: 8
            }
          },
          scales: {
            x: {
              grid: { color: gridColor },
              ticks: { color: textColor, font: { family: 'Pretendard' }, maxTicksLimit: 12 }
            },
            y: {
              grid: { color: gridColor },
              ticks: { color: textColor, font: { family: 'Pretendard' } },
              title: { display: true, text: '평균 이용률(%)', color: textColor }
            }
          }
        }
      });
    }

  } catch (err) {
    console.error('차트 렌더링 실패:', err);
  }
}
