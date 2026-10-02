// ==========================================================================
// DataSolve Studio - Problem Solving & Diagnostic Interaction Logic
// ==========================================================================

async function submitProblemSolve(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const jsonPayload = {};
  formData.forEach((value, key) => { jsonPayload[key] = value; });

  const resultContainer = document.getElementById('solve-result-container');
  if (resultContainer) {
    resultContainer.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem;">
        <div style="font-size: 1.8rem; margin-bottom: 0.8rem;">⚙️</div>
        <p style="font-weight: 600; color: var(--text-secondary);">수집된 데이터셋과 대조 분석 중입니다...</p>
      </div>
    `;
  }

  try {
    const res = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(jsonPayload)
    });
    const result = await res.json();

    if (result.success) {
      renderSolutionResult(result);
      if (typeof drawRouteOnMap === 'function' && result.route_coords) {
        drawRouteOnMap(result.route_coords, result.summary_title);
      }
      
      // 추천 주차장 마커 팝업 오픈 및 알림
      if (result.recommended_lot) {
        if (typeof showToast === 'function') {
          const payBadge = result.recommended_lot.pay ? ` [${result.recommended_lot.pay}]` : '';
          showToast(`🚗 추천 주차장: [${result.recommended_lot.district}] ${result.recommended_lot.name}${payBadge} (잔여 ${result.recommended_lot.available}면)`, 'success');
        }
        if (typeof markerObjects !== 'undefined' && markerObjects) {
          const target = markerObjects.find(m => 
            (m.pt.pklt_cd && String(m.pt.pklt_cd) === String(result.recommended_lot.pklt_cd)) ||
            (m.pt.title && (m.pt.title.includes(result.recommended_lot.name) || result.recommended_lot.name.includes(m.pt.title)))
          );
          if (target && target.marker) {
            setTimeout(() => {
              target.marker.openPopup();
            }, 600);
          }
        }
      }

      if (window.confetti && (result.risk_level.includes('안전') || result.risk_level.includes('우수') || result.risk_level.includes('여유'))) {
        window.confetti({ particleCount: 40, spread: 50, origin: { y: 0.7 } });
      }
    } else {
      if (typeof showToast === 'function') {
        showToast(result.message || '분석 중 오류가 발생했습니다.', 'error');
      }
      if (resultContainer) {
        resultContainer.innerHTML = `<div class="insight-item" style="border-left-color: var(--danger); color: var(--danger);">${result.message || '분석 중 오류가 발생했습니다.'}</div>`;
      }
    }
  } catch (err) {
    console.error(err);
    if (typeof showToast === 'function') {
      showToast('통신 오류가 발생했습니다.', 'error');
    }
    if (resultContainer) {
      resultContainer.innerHTML = `<div class="insight-item" style="border-left-color: var(--danger); color: var(--danger);">통신 오류가 발생했습니다.</div>`;
    }
  }
}

function renderSolutionResult(result) {
  const container = document.getElementById('solve-result-container');
  if (!container) return;

  const riskClass = (result.risk_level.includes('고위험') || result.risk_level.includes('개선필요') || result.risk_level.includes('혼잡')) 
    ? 'high-risk' 
    : ((result.risk_level.includes('주의') || result.risk_level.includes('보통')) ? 'medium-risk' : 'low-risk');

  const riskColor = riskClass === 'high-risk' ? 'var(--danger)' : (riskClass === 'medium-risk' ? 'var(--warning)' : 'var(--success)');

  let actionHtml = '';
  if (result.action_plan && result.action_plan.length) {
    actionHtml = result.action_plan.map(tip => `
      <div class="compact-action-tip">
        ${tip}
      </div>
    `).join('');
  }

  container.innerHTML = `
    <div class="compact-result-box ${riskClass}">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
        <span style="font-size: 0.76rem; font-weight: 700; color: ${riskColor}; letter-spacing: 0.3px;">${result.summary_title}</span>
        <span class="scenario-badge" style="font-size: 0.68rem; padding: 1px 7px; color: ${riskColor}; border-color: ${riskColor};">
          ${result.risk_level}
        </span>
      </div>

      <div class="compact-score-banner">
        <div>
          <div class="compact-score-num" style="color: ${riskColor};">
            ${result.risk_percentage}%
          </div>
          <div style="font-size: 0.68rem; color: var(--text-muted); font-weight: 600;">주차 이용률</div>
        </div>
        <div style="border-left: 1px solid var(--border-color); padding-left: 0.8rem; flex: 1; margin-left: 0.8rem;">
          <div style="font-size: 0.82rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.15rem;">
            ${result.top_concern}
          </div>
          <div style="font-size: 0.72rem; color: var(--text-secondary); line-height: 1.35;">
            ${result.cohort_stats}
          </div>
        </div>
      </div>

      <div>
        <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.3rem;">
          <i data-lucide="check-circle" style="width: 13px; height: 13px; color: var(--accent-primary);"></i>
          <span>맞춤 실행 솔루션 (Action Plan)</span>
        </div>
        ${actionHtml}
      </div>
    </div>
  `;

  if (window.lucide) {
    window.lucide.createIcons();
  }
}

