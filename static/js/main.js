// ==========================================================================
// DataSolve Studio - Global Logic & Scenario Switcher
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initLucideIcons();
});

function initLucideIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// --- Theme Switcher ---
function initTheme() {
  const savedTheme = localStorage.getItem('datasolve_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  const themeBtn = document.getElementById('theme-toggle-btn');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', nextTheme);
      localStorage.setItem('datasolve_theme', nextTheme);
      updateThemeIcon(nextTheme);
      showToast(`${nextTheme === 'dark' ? '다크' : '라이트'} 모드로 전환되었습니다.`, 'info');
    });
  }
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
    initLucideIcons();
  }
}

// --- Toast Feedback ---
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  
  let iconName = 'check-circle';
  let iconColor = 'var(--success)';
  if (type === 'error') {
    iconName = 'alert-triangle';
    iconColor = 'var(--danger)';
  } else if (type === 'info') {
    iconName = 'info';
    iconColor = 'var(--accent-primary)';
  }

  toast.innerHTML = `
    <i data-lucide="${iconName}" style="color: ${iconColor}; width: 20px; height: 20px;"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  initLucideIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

// --- Scenario Switcher ---
async function switchScenario(scenario) {
  try {
    const res = await fetch('/api/scenario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenario })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`[${scenario}] 시나리오로 변경되었습니다. 대시보드를 새로고침합니다.`, 'success');
      setTimeout(() => location.reload(), 400);
    } else {
      showToast(data.message || '시나리오 변경 실패', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('서버 통신 오류', 'error');
  }
}

// --- Data Collect / Refresh Trigger ---
async function triggerCollect() {
  const btn = document.getElementById('btn-collect-refresh');
  if (btn) btn.disabled = true;

  showToast('데이터 파이프라인 수집 및 갱신을 실행하는 중입니다...', 'info');

  try {
    const res = await fetch('/api/collect', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      setTimeout(() => location.reload(), 500);
    } else {
      showToast(data.message || '수집 실패', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('수집 중 통신 오류가 발생했습니다.', 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// --- Custom CSV Upload Handler ---
async function handleCsvUpload(event) {
  event.preventDefault();
  const fileInput = document.getElementById('csv-file-input');
  if (!fileInput || !fileInput.files.length) {
    showToast('업로드할 CSV 파일을 선택해주세요.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  showToast('CSV 파일을 업로드하고 분석 모델을 구성하는 중...', 'info');

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      setTimeout(() => window.location.href = '/', 600);
    } else {
      showToast(data.message || '업로드 실패', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('업로드 중 네트워크 오류가 발생했습니다.', 'error');
  }
}
