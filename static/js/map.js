// ==========================================================================
// 대구 분진흡입차량 운행 분석 & 실시간 대기정보(air.daegu.go.kr) 관제 JS
// 네이버 지도 스타일 통합 맵 엔진 (일반지도 ↔ 위성사진, 행정구역 & 도로망 오버레이)
// ==========================================================================

let allVehicles = [];
let allRoutes = [];
let selectedDistrict = null;
let selectedDongName = null;
let selectedRouteId = null;
let currentAirDate = null; // null이면 현재 실시간(오늘) 날짜 자동 사용
let currentMasterView = 'clean'; // 'clean' (일반/다크 도로 지도), 'satellite' (고해상도 위성사진)
let currentNaverBaseMap = 'clean'; // 'clean' 또는 'satellite'
let currentStationCode = '701'; // 기본: 수창동(중구)

// 네이버 지도 스타일 오버레이 토글 상태
let isDistrictOverlayOn = true;
let isRoutesOverlayOn = true;

// Leaflet 레이어 참조
let leafletMapInstance = null;
let darkOSMTileLayer = null;
let esriSatelliteTileLayer = null;
let leafletDongLayer = null;
let selectedDongHighlightLayer = null; // 선택된 동 전용 최상단 네온 SVG 하이라이트 레이어
let leafletRouteLayerGroup = null;
let leafletRoutePolylines = [];
let daeguDongGeoJsonData = null;
let currentlyHoveredDongLayer = null;

// 마우스 드래그 & 클릭 판별 제어 상태 변수
let isMapMouseDown = false;
let isMapDragging = false;
let mapMouseDownTime = 0;
let mapMouseDownPos = null;
let lastDragEndTime = 0;
let justClickedDong = false; // 동 클릭 시 맵 전역 초기화 이벤트 방지 플래그

function dismissAllTooltipsAndHovers() {
  if (currentlyHoveredDongLayer) {
    if (currentlyHoveredDongLayer.feature) {
      currentlyHoveredDongLayer.setStyle(getDongStyle(currentlyHoveredDongLayer.feature));
    } else if (leafletDongLayer) {
      leafletDongLayer.resetStyle(currentlyHoveredDongLayer);
    }
    currentlyHoveredDongLayer.closeTooltip();
    currentlyHoveredDongLayer = null;
  }
  if (leafletMapInstance) {
    leafletMapInstance.eachLayer(l => {
      if (l.closeTooltip) l.closeTooltip();
    });
  }
}

// 영문 ID <-> 한글 구·군 이름 매핑
const districtIdToName = {
  'junggu': '중구',
  'donggu': '동구',
  'seogu': '서구',
  'namgu': '남구',
  'bukgu': '북구',
  'suseonggu': '수성구',
  'dalseogu': '달서구',
  'dalseonggun': '달성군'
};

const districtNameToId = {
  '중구': 'junggu',
  '동구': 'donggu',
  '서구': 'seogu',
  '남구': 'namgu',
  '북구': 'bukgu',
  '수성구': 'suseonggu',
  '달서구': 'dalseogu',
  '달성군': 'dalseonggun'
};

// 자치구별 대표 대기측정소 매핑
const districtToStation = {
  '중구': '701',    // 수창동
  '남구': '702',    // 대명동
  '수성구': '703',  // 만촌동
  '동구': '704',    // 신암동
  '북구': '705',    // 노원동
  '서구': '709',    // 이현동
  '달서구': '710',  // 호산동
  '달성군': '714'   // 다사읍
};

// ==========================================================================
// 대기질 4단계 등급별 공식 색상 정의 (AirKorea / 대구 실시간 대기정보 기준)
// ==========================================================================
const airGradeColors = {
  good: '#3b82f6',       // 1단계 좋음: 파랑 (0 ~ 30 ㎍/㎥)
  moderate: '#10b981',   // 2단계 보통: 초록 (31 ~ 80 ㎍/㎥)
  bad: '#f59e0b',        // 3단계 나쁨: 주황 (81 ~ 150 ㎍/㎥)
  veryBad: '#ef4444'     // 4단계 매우나쁨: 빨강 (151 ㎍/㎥ ~)
};

// 자치구별 미세먼지(PM10) 대기질 기본 데이터 및 실시간 동기화 상태
const defaultDistrictAirData = {
  '중구': { pm10: 67, level: 2, text: '보통', color: '#10b981' },
  '남구': { pm10: 63, level: 2, text: '보통', color: '#10b981' },
  '수성구': { pm10: 74, level: 2, text: '보통', color: '#10b981' },
  '동구': { pm10: 79, level: 2, text: '보통', color: '#10b981' },
  '북구': { pm10: 85, level: 3, text: '나쁨', color: '#f59e0b' },
  '서구': { pm10: 91, level: 3, text: '나쁨', color: '#f59e0b' },
  '달서구': { pm10: 88, level: 3, text: '나쁨', color: '#f59e0b' },
  '달성군': { pm10: 58, level: 2, text: '보통', color: '#10b981' }
};

let currentDistrictAirData = { ...defaultDistrictAirData };

// PM10 수치 기반 4단계 대기질 등급(좋음/보통/나쁨/매우나쁨) 및 색상 판정
function getAirGradeFromPm10(pm10) {
  const val = Number(pm10) || 0;
  if (val <= 30) {
    return { level: 1, text: '좋음', color: '#3b82f6', bgClass: 'bg-air-good' };
  } else if (val <= 80) {
    return { level: 2, text: '보통', color: '#10b981', bgClass: 'bg-air-moderate' };
  } else if (val <= 150) {
    return { level: 3, text: '나쁨', color: '#f59e0b', bgClass: 'bg-air-bad' };
  } else {
    return { level: 4, text: '매우나쁨', color: '#ef4444', bgClass: 'bg-air-very-bad' };
  }
}

const stationCodeToDistrict = {
  '701': '중구',
  '702': '남구',
  '703': '수성구',
  '704': '동구',
  '705': '북구',
  '707': '수성구',
  '708': '북구',
  '709': '서구',
  '710': '달서구',
  '711': '달성군',
  '712': '수성구',
  '713': '동구',
  '714': '달성군',
  '715': '동구',
  '716': '달서구',
  '717': '달성군',
  '718': '달서구',
  '719': '북구',
  '720': '남구',
  '721': '동구',
  '802': '서구',
  '803': '달서구'
};

async function fetchDistrictAirData() {
  try {
    const res = await fetch('/api/air/districts');
    const result = await res.json();
    if (result.success && result.districts) {
      currentDistrictAirData = { ...defaultDistrictAirData, ...result.districts };
      if (leafletDongLayer) {
        leafletDongLayer.setStyle(getDongStyle);
      }
    }
  } catch (err) {
    console.error('자치구별 대기정보 로드 실패:', err);
  }
}

// --------------------------------------------------------------------------
// 앱 초기화 라이프사이클
// --------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  // 1. 백엔드 분진차량 및 경로 데이터 로드
  await loadBackendData();

  // 1-2. 8개 자치구 미세먼지(PM10) 대기질 데이터 비동기 로드
  await fetchDistrictAirData();

  // 2. 통합 인터랙티브 지도 초기화 (일반/위성사진 베이스맵)
  initRoadLeafletMap();

  // 3. 대구 142개 읍·면·동 행정구역 GeoJSON 레이어 비동기 로드 및 바인딩
  await loadDaeguDongGeoJson();

  // 4. 전역 이벤트 리스너 등록
  setupEventListeners();

  // 5. 실시간 대기정보 첫 로드
  await fetchAirData(currentStationCode);

  // 6. 초기 화면: 특정 자치구 강제 선택 없이 대구 전역 균일 조망
  if (leafletMapInstance && leafletRoutePolylines && leafletRoutePolylines.length > 0) {
    const allBounds = [];
    leafletRoutePolylines.forEach(p => {
      if (p.routeData && p.routeData.points) {
        p.routeData.points.forEach(pt => allBounds.push(pt));
      }
    });
    if (allBounds.length > 0) {
      leafletMapInstance.fitBounds(allBounds, { padding: [50, 50], maxZoom: 12 });
    }
  }

  // 7. 기본 베이스맵(일반지도 또는 대기 중인 뷰) 동기화
  const targetView = window._pendingMasterView || currentMasterView || 'clean';
  setMasterView(targetView);
});

// 1. 백엔드 분진차량 분석 데이터 로드
async function loadBackendData() {
  try {
    const res = await fetch('/api/analysis');
    const result = await res.json();
    if (result.success && result.data) {
      allVehicles = result.data.vehicles || [];
      allRoutes = result.data.routes || [];

      // 백엔드 모니터링 측정소 기본 PM10 데이터 병합
      if (result.data.stations && Array.isArray(result.data.stations)) {
        result.data.stations.forEach(s => {
          if (s.district && s.pm10) {
            const grade = getAirGradeFromPm10(s.pm10);
            currentDistrictAirData[s.district] = {
              district: s.district,
              sttn_name: s.name,
              pm10: s.pm10,
              level: grade.level,
              text: grade.text,
              color: grade.color
            };
          }
        });
      }
    }
  } catch (err) {
    console.error('분석 데이터 로드 실패:', err);
  }
}

// --------------------------------------------------------------------------
// 2. 대구 142개 동·읍·면 GeoJSON 레이어 로드 & 렌더링
// --------------------------------------------------------------------------
async function loadDaeguDongGeoJson() {
  if (!leafletMapInstance) return;

  try {
    const res = await fetch('/static/data/daegu_dong.geojson?v=' + Date.now());
    daeguDongGeoJsonData = await res.json();

    if (leafletDongLayer && leafletMapInstance.hasLayer(leafletDongLayer)) {
      leafletMapInstance.removeLayer(leafletDongLayer);
    }

    leafletDongLayer = L.geoJSON(daeguDongGeoJsonData, {
      style: getDongStyle,
      onEachFeature: onEachDongFeature
    });
    window.leafletDongLayer = leafletDongLayer;

    if (isDistrictOverlayOn) {
      leafletDongLayer.addTo(leafletMapInstance);
      leafletDongLayer.bringToBack();
    }

    // 도로망 노선이 항상 폴리곤 위에 오도록 유지
    if (leafletRouteLayerGroup && leafletMapInstance.hasLayer(leafletRouteLayerGroup)) {
      leafletRouteLayerGroup.bringToFront();
    }

    if (selectedDistrict) {
      leafletDongLayer.setStyle(getDongStyle);
    }
  } catch (err) {
    console.error('대구 행정구역 GeoJSON 로드 실패:', err);
  }
}

// 선택된 동 또는 자치구의 실제 행정구역 SVG 경계선 전용 최상단 네온 하이라이트 오버레이
function updateDongHighlightOverlay(districtName, dongName = null) {
  if (!leafletMapInstance || !daeguDongGeoJsonData) return;

  // 기존 하이라이트 오버레이 제거
  if (selectedDongHighlightLayer && leafletMapInstance.hasLayer(selectedDongHighlightLayer)) {
    leafletMapInstance.removeLayer(selectedDongHighlightLayer);
    selectedDongHighlightLayer = null;
  }

  // 타겟 Feature(들) 필터링 (공백 및 특수문자 안전 처리)
  let targetFeatures = [];
  if (dongName) {
    // 특정 동 선택 시: 해당 1개 동의 실제 SVG 곡선 경계선
    targetFeatures = daeguDongGeoJsonData.features.filter(f => {
      if (!f.properties) return false;
      const fDist = (f.properties.district || '').trim();
      const fDong = (f.properties.dong || '').trim();
      const tDist = (districtName || '').trim();
      const tDong = (dongName || '').trim();
      return fDist === tDist && (fDong === tDong || fDong.includes(tDong) || tDong.includes(fDong));
    });
  } else if (districtName) {
    // 자치구 전체 선택 시: 해당 자치구 내 동들의 실제 SVG 경계선
    targetFeatures = daeguDongGeoJsonData.features.filter(f => {
      if (!f.properties) return false;
      const fDist = (f.properties.district || '').trim();
      const tDist = (districtName || '').trim();
      return fDist === tDist;
    });
  }

  if (targetFeatures.length > 0) {
    selectedDongHighlightLayer = L.geoJSON(targetFeatures, {
      style: {
        fill: false,
        fillOpacity: 0, // 내부는 100% 투명하게 하여 이전 투명도 완벽 보존
        color: '#38bdf8', // 깔끔하고 선명한 사이언 외곽선
        weight: 3, // 과하지 않고 또렷한 외곽선 두께
        opacity: 1,
        dashArray: '',
        className: 'selected-dong-neon-path'
      },
      interactive: false // 마우스 이벤트는 아래 레이어로 통과
    });

    selectedDongHighlightLayer.addTo(leafletMapInstance);
    selectedDongHighlightLayer.bringToFront();

    // 도로망 노선이 항상 최상단에 오도록 유지
    if (leafletRouteLayerGroup && leafletMapInstance.hasLayer(leafletRouteLayerGroup)) {
      leafletRouteLayerGroup.bringToFront();
    }
  }
}

// 동 폴리곤 스타일 계산 (미세먼지 좋음/보통/나쁨/매우나쁨 등급 기반 컬러링 및 실제 SVG 테두리 곡선 강조)
function getDongStyle(feature) {
  const dist = (feature.properties.district || '').trim();
  const dong = (feature.properties.dong || '').trim();
  const isSelectedDong = selectedDongName && (dong === selectedDongName.trim() || dong.includes(selectedDongName.trim())) && (!selectedDistrict || dist === selectedDistrict.trim());
  const isSelectedDist = selectedDistrict && dist === selectedDistrict.trim();

  // 구(Gu) 고유색 대신 자치구의 미세먼지(PM10) 대기질 등급 색상 적용
  const airInfo = currentDistrictAirData[dist] || defaultDistrictAirData[dist] || { pm10: 70, level: 2, text: '보통', color: '#10b981' };
  const airColor = airInfo.color || '#10b981';

  // 1. 특정 동(Dong)이 선택된 경우: 내부 투명도(0.28) 유지 + 사이언 외곽선 강조
  if (isSelectedDong) {
    return {
      fillColor: airColor,
      fillOpacity: 0.28, // 기존 대기색 투명도(0.28) 그대로 유지!
      color: '#38bdf8', // 깔끔한 사이언 외곽선
      weight: 3,        // 절제된 외곽선 두께
      opacity: 1,
      dashArray: ''
    };
  }

  // 2. 특정 자치구(구/군)가 선택된 경우: 내부 투명도는 기본 투명도(0.28) 유지하고 구 외곽선 강조
  if (isSelectedDist && !selectedDongName) {
    return {
      fillColor: airColor,
      fillOpacity: 0.28,
      color: '#38bdf8',
      weight: 2,
      opacity: 0.9,
      dashArray: ''
    };
  }

  // 3. 모든 비선택 구역도 옅어지지 않고 동일하게 원래 투명도(0.28) 유지
  return {
    fillColor: airColor,
    fillOpacity: 0.28,
    color: airColor,
    weight: 1.2,
    opacity: 0.65,
    dashArray: '2'
  };
}

// 각 동 폴리곤에 대한 이벤트 및 툴팁 바인딩
function onEachDongFeature(feature, layer) {
  const dong = feature.properties.dong;
  const dist = feature.properties.district;
  const fullName = feature.properties.fullName || `대구광역시 ${dist} ${dong}`;

  const airInfo = currentDistrictAirData[dist] || defaultDistrictAirData[dist] || { pm10: 70, level: 2, text: '보통', color: '#10b981' };

  layer.bindTooltip(`
    <div style="font-family: inherit;">
      <div style="font-weight: 700; font-size: 0.85rem; color: #f8fafc; margin-bottom: 3px;">
        ${dist} <span style="color: #38bdf8;">${dong}</span>
      </div>
      <div style="display: flex; align-items: center; gap: 6px; font-size: 0.74rem; color: #cbd5e1;">
        <span>미세먼지(PM10):</span>
        <strong style="color: ${airInfo.color}; font-weight: 700;">${airInfo.pm10}㎍/㎥</strong>
        <span style="background: ${airInfo.color}25; color: ${airInfo.color}; border: 1px solid ${airInfo.color}60; padding: 1px 5px; border-radius: 4px; font-size: 0.68rem; font-weight: 600;">${airInfo.text}</span>
      </div>
    </div>
  `, {
    sticky: true,
    className: 'dong-leaflet-tooltip',
    direction: 'auto',
    opacity: 0.95
  });

  // Leaflet 기본 _openTooltip 가로채기 (드래그/마우스누름/드래그 직후 툴팁 자동 팝업 원천 봉쇄)
  const origOpenTooltip = layer._openTooltip;
  layer._openTooltip = function(e) {
    // 1. 마우스 좌클릭이 눌려있는 상태 (드래그 중이거나 홀드 중)
    if (e && e.originalEvent && e.originalEvent.buttons !== 0) return;
    // 2. 지도 드래그 또는 마우스다운 상태 플래그
    if (isMapMouseDown || isMapDragging) return;
    // 3. 드래그 직후 350ms 이내 (드래그 종료 지점에서의 불필요한 자동 툴팁 팝업 방지)
    if (Date.now() - lastDragEndTime < 350) return;

    if (origOpenTooltip) {
      origOpenTooltip.call(this, e);
    }
  };

  layer.on({
    mouseover: function(e) {
      // 마우스 버튼이 눌려 있는 상태(드래그 중이거나 홀드 중), 또는 드래그 직후에는 호버 툴팁과 하이라이트 생성 완전 차단!
      if (e.originalEvent && e.originalEvent.buttons !== 0) return;
      if (isMapMouseDown || isMapDragging) return;
      if (Date.now() - lastDragEndTime < 350) return;

      const l = e.target;

      // 최신 미세먼지 정보로 툴팁 실시간 반영
      const latestAir = currentDistrictAirData[dist] || defaultDistrictAirData[dist] || { pm10: 70, level: 2, text: '보통', color: '#10b981' };
      layer.setTooltipContent(`
        <div style="font-family: inherit;">
          <div style="font-weight: 700; font-size: 0.85rem; color: #f8fafc; margin-bottom: 3px;">
            ${dist} <span style="color: #38bdf8;">${dong}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 6px; font-size: 0.74rem; color: #cbd5e1;">
            <span>미세먼지(PM10):</span>
            <strong style="color: ${latestAir.color}; font-weight: 700;">${latestAir.pm10}㎍/㎥</strong>
            <span style="background: ${latestAir.color}25; color: ${latestAir.color}; border: 1px solid ${latestAir.color}60; padding: 1px 5px; border-radius: 4px; font-size: 0.68rem; font-weight: 600;">${latestAir.text}</span>
          </div>
        </div>
      `);

      if (currentlyHoveredDongLayer && currentlyHoveredDongLayer !== l) {
        if (leafletDongLayer) {
          leafletDongLayer.resetStyle(currentlyHoveredDongLayer);
        }
        currentlyHoveredDongLayer.closeTooltip();
      }
      currentlyHoveredDongLayer = l;

      l.setStyle({
        fillOpacity: 0.38,
        color: '#ffffff',
        weight: 2,
        opacity: 0.95
      });
    },
    mouseout: function(e) {
      const l = e.target;
      if (l.feature) {
        l.setStyle(getDongStyle(l.feature));
      } else if (leafletDongLayer) {
        leafletDongLayer.resetStyle(l);
      }
      l.closeTooltip();
      if (currentlyHoveredDongLayer === l) {
        currentlyHoveredDongLayer = null;
      }
    },
    mousedown: function(e) {
      layer._mouseDownTime = Date.now();
      layer._mouseDownPos = e.containerPoint;
    },
    click: function(e) {
      if (e.originalEvent) {
        L.DomEvent.stopPropagation(e);
      }

      // 12px 이상 명백히 마우스를 움직였거나 지도 이동 중인 경우만 드래그로 판정하여 무시
      let movedDistance = 0;
      if (layer._mouseDownPos && e.containerPoint) {
        movedDistance = layer._mouseDownPos.distanceTo(e.containerPoint);
      }
      if (isMapDragging || movedDistance > 12) {
        return;
      }

      // 맵 빈 공간 클릭 시 즉각적인 선택 해제 방지 플래그
      justClickedDong = true;
      setTimeout(() => { justClickedDong = false; }, 350);

      dismissAllTooltipsAndHovers();
      selectDistrictAndDong(dist, dong, fullName);
    }
  });
}

// --------------------------------------------------------------------------
// 3. 네이버 지도 스타일 3-Way 뷰 및 오버레이 컨트롤러
// --------------------------------------------------------------------------
// 3. 네이버 지도 스타일 2-Way 베이스맵([일반지도] ↔ [위성사진]) 및 오버레이 컨트롤러
// --------------------------------------------------------------------------
function setMasterView(viewType) {
  if (viewType === 'svg') viewType = 'clean';
  currentMasterView = viewType;

  setNaverBaseMap(viewType);

  if (leafletMapInstance) {
    setTimeout(() => {
      leafletMapInstance.invalidateSize();
      if (selectedDistrict) {
        highlightLeafletDistrict(selectedDistrict);
      }
    }, 50);
  }

  updateNaverControlsUI();
}

function setNaverBaseMap(type) {
  currentNaverBaseMap = type;
  if (!leafletMapInstance) return;

  if (type === 'satellite') {
    // 고해상도 위성영상으로 전환 (위치/줌/레이어 유지)
    if (darkOSMTileLayer && leafletMapInstance.hasLayer(darkOSMTileLayer)) {
      leafletMapInstance.removeLayer(darkOSMTileLayer);
    }
    if (esriSatelliteTileLayer && !leafletMapInstance.hasLayer(esriSatelliteTileLayer)) {
      esriSatelliteTileLayer.addTo(leafletMapInstance);
      esriSatelliteTileLayer.bringToBack();
    }
  } else {
    // 일반/선명한 다크 지도로 전환 (위치/줌/레이어 유지)
    if (esriSatelliteTileLayer && leafletMapInstance.hasLayer(esriSatelliteTileLayer)) {
      leafletMapInstance.removeLayer(esriSatelliteTileLayer);
    }
    if (darkOSMTileLayer && !leafletMapInstance.hasLayer(darkOSMTileLayer)) {
      darkOSMTileLayer.addTo(leafletMapInstance);
      darkOSMTileLayer.bringToBack();
    }
  }

  // 레이어 계층 순서 보정
  if (leafletDongLayer && leafletMapInstance.hasLayer(leafletDongLayer)) {
    leafletDongLayer.bringToBack();
  }
  if (leafletRouteLayerGroup && leafletMapInstance.hasLayer(leafletRouteLayerGroup)) {
    leafletRouteLayerGroup.bringToFront();
  }
}

function toggleNaverOverlay(type) {
  if (type === 'district') {
    isDistrictOverlayOn = !isDistrictOverlayOn;
    if (leafletMapInstance) {
      if (isDistrictOverlayOn) {
        if (leafletDongLayer && !leafletMapInstance.hasLayer(leafletDongLayer)) {
          leafletDongLayer.addTo(leafletMapInstance);
          leafletDongLayer.bringToBack();
        }
      } else {
        if (leafletDongLayer && leafletMapInstance.hasLayer(leafletDongLayer)) {
          leafletMapInstance.removeLayer(leafletDongLayer);
        }
      }
    }
  } else if (type === 'routes') {
    isRoutesOverlayOn = !isRoutesOverlayOn;
    if (leafletMapInstance) {
      if (isRoutesOverlayOn) {
        if (leafletRouteLayerGroup && !leafletMapInstance.hasLayer(leafletRouteLayerGroup)) {
          leafletRouteLayerGroup.addTo(leafletMapInstance);
        }
      } else {
        if (leafletRouteLayerGroup && leafletMapInstance.hasLayer(leafletRouteLayerGroup)) {
          leafletMapInstance.removeLayer(leafletRouteLayerGroup);
        }
      }
    }
  }

  if (leafletMapInstance && leafletRouteLayerGroup && leafletMapInstance.hasLayer(leafletRouteLayerGroup)) {
    leafletRouteLayerGroup.bringToFront();
  }

  // UI 버튼 상태 갱신
  updateNaverControlsUI();
}

// 상단 헤더 및 우측 플로팅 버튼 활성화 상태 동기화
function updateNaverControlsUI() {
  const btnClean = document.getElementById('btn-basemap-clean');
  const btnSat = document.getElementById('btn-basemap-satellite');
  const btnDist = document.getElementById('btn-overlay-district');
  const btnRoutes = document.getElementById('btn-overlay-routes');

  const nftStd = document.getElementById('nft-btn-std');
  const nftSat = document.getElementById('nft-btn-sat');
  const nftDist = document.getElementById('nft-layer-dist');
  const nftRoute = document.getElementById('nft-layer-route');

  const isClean = currentMasterView === 'clean';
  const isSat = currentMasterView === 'satellite';

  // 1. 맵 뷰 타입 동기화
  if (btnClean) btnClean.classList.toggle('active', isClean);
  if (btnSat) btnSat.classList.toggle('active', isSat);

  if (nftStd) nftStd.classList.toggle('active', isClean);
  if (nftSat) nftSat.classList.toggle('active', isSat);

  // 2. 오버레이 레이어 동기화
  if (btnDist) btnDist.classList.toggle('active', isDistrictOverlayOn);
  if (nftDist) nftDist.classList.toggle('active', isDistrictOverlayOn);

  if (btnRoutes) btnRoutes.classList.toggle('active', isRoutesOverlayOn);
  if (nftRoute) nftRoute.classList.toggle('active', isRoutesOverlayOn);

  if (window.lucide) {
    lucide.createIcons();
  }
}

// --------------------------------------------------------------------------
// 4. 대구 실시간 대기정보(air.daegu.go.kr) 크롤링 데이터 조회 및 렌더링
// --------------------------------------------------------------------------
async function fetchAirData(sttnCd = '701', dateStr = undefined, force = false) {
  currentStationCode = sttnCd;
  if (dateStr !== undefined) {
    currentAirDate = dateStr;
  }

  try {
    const query = currentAirDate ? `sttn_cd=${sttnCd}&date=${encodeURIComponent(currentAirDate)}` : `sttn_cd=${sttnCd}`;
    const res = await fetch(`/api/air/realtime?${query}`);
    const result = await res.json();

    if (result.success && result.data) {
      const airData = result.data;
      updateAirUi(airData);
      renderAirTable(airData.records);

      // 해당 측정소가 속한 자치구의 미세먼지 수치 실시간 갱신 & 지도 반영
      if (airData.latest && airData.latest.pm10 && airData.latest.pm10.value) {
        const val = parseInt(airData.latest.pm10.value, 10);
        const distName = stationCodeToDistrict[sttnCd];
        if (distName && !isNaN(val)) {
          const grade = getAirGradeFromPm10(val);
          currentDistrictAirData[distName] = {
            district: distName,
            sttn_cd: sttnCd,
            pm10: val,
            level: grade.level,
            text: grade.text,
            color: grade.color
          };
          if (leafletDongLayer) {
            leafletDongLayer.setStyle(getDongStyle);
          }
        }
      }
    }
  } catch (err) {
    console.error('실시간 대기정보 조회 실패:', err);
  }
}

function updateAirUi(airData) {
  const latest = airData.latest;
  const sttnName = airData.station_name || '수창동(중구)';

  // 1. 헤더 상단 라이브 칩
  const liveStation = document.getElementById('air-live-station');
  const livePm10 = document.getElementById('air-live-pm10');
  const livePm25 = document.getElementById('air-live-pm25');
  if (liveStation) liveStation.textContent = sttnName;
  if (livePm10 && latest) livePm10.textContent = latest.pm10.value;
  if (livePm25 && latest) livePm25.textContent = latest.pm25.value;

  // 2. 좌측 퀵 카드
  const qStation = document.getElementById('quick-air-station');
  const qTime = document.getElementById('quick-air-time');
  const qPm10Val = document.getElementById('quick-pm10-val');
  const qPm10Tag = document.getElementById('quick-pm10-tag');
  const qPm25Val = document.getElementById('quick-pm25-val');
  const qPm25Tag = document.getElementById('quick-pm25-tag');
  const qCaiVal = document.getElementById('quick-cai-val');
  const qCaiSub = document.getElementById('quick-cai-sub');
  const qCaiTag = document.getElementById('quick-cai-tag');

  if (qStation) qStation.textContent = sttnName;
  if (latest) {
    if (qTime) qTime.textContent = `${latest.time.split(' ')[1]} 기준`;
    if (qPm10Val) qPm10Val.textContent = latest.pm10.value;
    if (qPm10Tag) {
      qPm10Tag.textContent = latest.pm10.grade.text;
      qPm10Tag.className = `qm-tag tag-${latest.pm10.grade.level === 1 ? 'good' : (latest.pm10.grade.level === 2 ? 'moderate' : 'bad')}`;
    }
    if (qPm25Val) qPm25Val.textContent = latest.pm25.value;
    if (qPm25Tag) {
      qPm25Tag.textContent = latest.pm25.grade.text;
      qPm25Tag.className = `qm-tag tag-${latest.pm25.grade.level === 1 ? 'good' : (latest.pm25.grade.level === 2 ? 'moderate' : 'bad')}`;
    }
    if (qCaiVal) qCaiVal.textContent = latest.cai.value;
    if (qCaiSub) qCaiSub.textContent = latest.cai.substance || 'O3';
    if (qCaiTag) {
      qCaiTag.textContent = latest.cai.grade.text;
      qCaiTag.className = `qm-tag tag-${latest.cai.grade.level === 1 ? 'good' : (latest.cai.grade.level === 2 ? 'moderate' : 'bad')}`;
    }
  }

  // 3. 셀렉트 박스 동기화
  const sttnSelect = document.getElementById('station-select');
  if (sttnSelect && sttnSelect.value !== airData.sttn_cd) {
    sttnSelect.value = airData.sttn_cd;
  }
  const modalSttnSelect = document.getElementById('modal-station-select');
  if (modalSttnSelect && modalSttnSelect.value !== airData.sttn_cd) {
    modalSttnSelect.value = airData.sttn_cd;
  }

  // 4. 조회 일자 인풋 및 공식 사이트 원문 링크 동적 갱신
  const dateInput = document.getElementById('modal-date-input');
  if (dateInput && airData.date) {
    dateInput.value = airData.date;
  }
  const officialLink = document.querySelector('.official-link');
  if (officialLink && airData.date) {
    officialLink.href = `https://air.daegu.go.kr/index.do?menu_id=00000801&menu_link=%2Ffront%2FrealTimeAir%2FrealTimeTotalAirView.do&sttn_cd=${airData.sttn_cd || '701'}&from=${airData.date}&fromtime=00&to=${airData.date}&totime=23`;
  }
}

function renderAirTable(records) {
  const tbody = document.getElementById('air-table-tbody');
  if (!tbody) return;

  function renderIcon(grade) {
    const lvl = grade.level;
    const txt = grade.text;
    let icon = 'smile';
    let cls = 'grade-good';
    if (lvl === 2) { icon = 'meh'; cls = 'grade-moderate'; }
    else if (lvl === 3) { icon = 'frown'; cls = 'grade-bad'; }
    else if (lvl === 4) { icon = 'alert-triangle'; cls = 'grade-very-bad'; }
    return `<span class="tbl-grade-icon ${cls}" title="${txt}"><i data-lucide="${icon}"></i></span>`;
  }

  const reversedRecords = [...records].reverse();

  tbody.innerHTML = reversedRecords.map(r => `
    <tr>
      <td style="font-weight: 600;">${r.time}</td>
      <td style="font-weight: 700; color: var(--accent-blue);">${r.cai.substance}</td>
      <td>${renderIcon(r.cai.grade)}</td>
      <td style="font-weight: 700;">${r.cai.value}</td>
      <td>${renderIcon(r.pm25.grade)}</td>
      <td style="font-weight: 700;">${r.pm25.value}</td>
      <td>${renderIcon(r.pm10.grade)}</td>
      <td class="col-pm10">${r.pm10.value}</td>
      <td>${renderIcon(r.o3.grade)}</td>
      <td>${r.o3.value}</td>
      <td>${renderIcon(r.co.grade)}</td>
      <td>${r.co.value}</td>
      <td>${renderIcon(r.so2.grade)}</td>
      <td>${r.so2.value}</td>
      <td>${renderIcon(r.no2.grade)}</td>
      <td>${r.no2.value}</td>
    </tr>
  `).join('');
}

async function openAirModal() {
  const modal = document.getElementById('air-modal');
  if (modal) {
    modal.style.display = 'flex';
    lucide.createIcons();
  }
  // Fetch real-time overall district air summary and render
  try {
    const res = await fetch('/api/air/districts');
    const result = await res.json();
    if (result.success && result.districts) {
      renderDistrictSummary(Object.values(result.districts));
    }
  } catch (err) {
    console.error('District summary fetch failed:', err);
  }
}

function closeAirModal() {
  const modal = document.getElementById('air-modal');
  if (modal) modal.style.display = 'none';
}

function renderDistrictSummary(districts) {
  const tbody = document.getElementById('district-summary-tbody');
  if (!tbody) return;
  const rows = districts.map(d => {
    const gradeText = d.text || '';
    const color = d.color || '#10b981';
    return `
      <tr>
        <td>${d.district}</td>
        <td>${d.pm10}</td>
        <td><span class="qm-tag" style="background:${color}25;color:${color};border:1px solid ${color}60;">
          ${gradeText}
        </span></td>
      </tr>`;
  }).join('');
  tbody.innerHTML = rows;
}


// --------------------------------------------------------------------------
// 5. 구·군 및 동 단위 통합 선택 & 지도 동기화
// --------------------------------------------------------------------------
function selectDistrict(districtName, routeId = null) {
  selectedDistrict = districtName;
  selectedDongName = null;
  selectedRouteId = routeId;

  // 좌측 드롭다운 동기화
  const selectEl = document.getElementById('district-filter');
  if (selectEl) selectEl.value = districtName;

  // 퀵 칩 동기화
  document.querySelectorAll('.district-chip').forEach(chip => {
    if (chip.getAttribute('data-district') === districtName) {
      chip.classList.add('active');
    } else {
      chip.classList.remove('active');
    }
  });

  // 실시간 대기측정소 동기화
  const targetStation = districtToStation[districtName];
  if (targetStation && targetStation !== currentStationCode) {
    fetchAirData(targetStation);
  }

  // 우측 하단 상세 카드 렌더링
  renderDetailCard(districtName, null, `대구광역시 ${districtName} 관제 권역`, routeId);

  // 선택된 자치구의 실제 SVG 경계선 전용 최상단 네온 오버레이 반영
  updateDongHighlightOverlay(districtName, null);

  // Leaflet 동 폴리곤 스타일 갱신
  if (leafletDongLayer) {
    leafletDongLayer.setStyle(getDongStyle);
  }

  // Leaflet 도로망 노선 스타일 갱신 및 포커싱 (단일 노선 선택 시 해당 노선만 단독 강조)
  highlightLeafletDistrict(districtName, routeId, true);
}

function selectDistrictAndDong(districtName, dongName, fullName, routeId = null) {
  selectedDistrict = districtName;
  selectedDongName = dongName;
  selectedRouteId = routeId;

  // 좌측 드롭다운 동기화
  const selectEl = document.getElementById('district-filter');
  if (selectEl) selectEl.value = districtName;

  // 퀵 칩 동기화
  document.querySelectorAll('.district-chip').forEach(chip => {
    if (chip.getAttribute('data-district') === districtName) {
      chip.classList.add('active');
    } else {
      chip.classList.remove('active');
    }
  });

  // 실시간 대기측정소 동기화
  const targetStation = districtToStation[districtName];
  if (targetStation && targetStation !== currentStationCode) {
    fetchAirData(targetStation);
  }

  // 우측 하단 상세 카드 렌더링
  renderDetailCard(districtName, dongName, fullName, routeId);

  // 선택된 동의 실제 SVG 곡선 경계선 전용 최상단 네온 오버레이 표출
  updateDongHighlightOverlay(districtName, dongName);

  // Leaflet 동 폴리곤 스타일 갱신 및 선택된 동을 최상단으로 올림
  if (leafletDongLayer) {
    leafletDongLayer.setStyle(getDongStyle);
    leafletDongLayer.eachLayer(l => {
      if (l.feature && l.feature.properties && l.feature.properties.dong === dongName) {
        l.bringToFront();
      }
    });
  }

  // Leaflet 도로망 노선 스타일 갱신 (동 클릭 시에는 카메라 강제 줌아웃 방지)
  highlightLeafletDistrict(districtName, routeId, false);
}

function highlightLeafletDistrict(districtName, targetRouteId = null, shouldFitBounds = true) {
  if (!leafletMapInstance) return;

  // 동 폴리곤 스타일 동기화 (선택된 구의 실제 SVG 경계선 테두리 강조)
  if (leafletDongLayer) {
    leafletDongLayer.setStyle(getDongStyle);
  }

  const distBounds = [];

  // 1. 행정구역 동 레이어에서 해당 자치구 영역 바운드 추출 (단일 노선 선택이 아닐 때만 자치구 바운드 사용)
  if (!targetRouteId && leafletDongLayer && shouldFitBounds) {
    leafletDongLayer.eachLayer(layer => {
      if (layer.feature && layer.feature.properties && layer.feature.properties.district === districtName) {
        const b = layer.getBounds();
        distBounds.push(b.getSouthWest());
        distBounds.push(b.getNorthEast());
      }
    });
  }

  // 2. 도로망 노선 스타일 갱신
  if (leafletRoutePolylines && leafletRoutePolylines.length > 0) {
    leafletRoutePolylines.forEach(p => {
      // [중요] 특정 노선을 직접 클릭한 경우: 오직 그 1개 노선만 단독 강조!
      if (targetRouteId) {
        if (p.routeData && p.routeData.id === targetRouteId) {
          p.setStyle({ color: '#c084fc', weight: 8.5, opacity: 1 });
          p.bringToFront();
          if (p.routeData.points && shouldFitBounds) {
            p.routeData.points.forEach(pt => distBounds.push(L.latLng(pt[0], pt[1])));
          }
        } else {
          // 다른 모든 노선은 딤드(은은하게) 처리
          p.setStyle({ color: '#7e22ce', weight: 3.5, opacity: 0.35 });
        }
      } else {
        // 좌측 자치구 필터를 클릭한 경우: 해당 자치구 권역 노선 강조
        if (p.routeData && p.routeData.district && p.routeData.district.includes(districtName)) {
          p.setStyle({ color: '#c084fc', weight: 7.5, opacity: 1 });
          p.bringToFront();
          if (p.routeData.points && shouldFitBounds) {
            p.routeData.points.forEach(pt => distBounds.push(L.latLng(pt[0], pt[1])));
          }
        } else {
          p.setStyle({ color: '#7e22ce', weight: 4, opacity: 0.55 });
        }
      }
    });
  }

  // 3. 해당 노선 또는 권역으로 부드럽게 화면 이동 (shouldFitBounds가 true일 때만)
  if (shouldFitBounds && distBounds.length > 0 && leafletMapInstance) {
    leafletMapInstance.fitBounds(L.latLngBounds(distBounds), { padding: [60, 60], maxZoom: 14 });
  }
}

// 7. 우측 하단 상세 카드 렌더링
function renderDetailCard(districtName, dongName = null, fullName = null, routeId = null) {
  const card = document.getElementById('detail-card');
  const tag = document.getElementById('detail-tag');
  const title = document.getElementById('detail-title');
  const metrics = document.getElementById('detail-metrics');

  if (!card) return;

  const vehicle = allVehicles.find(v => v.district === districtName) || allVehicles[0] || {
    name: `${districtName} 관제차량`,
    model: '16톤 친환경 분진흡입차',
    improvement: { distance_reduction_pct: 18.4, duration_reduction_pct: 22.1, pm10_reduction_pct: 35.8, dust_efficiency_gain_pct: 28.5 },
    before_stats: { distance_km: 42.5, duration_min: 165, pm10_avg_after: 48 },
    after_stats: { distance_km: 34.7, duration_min: 128, pm10_avg_after: 31, dust_collected_kg: 84.5 }
  };
  const route = routeId ? (allRoutes.find(r => r.id === routeId) || allRoutes.find(r => r.district && r.district.includes(districtName))) : (allRoutes.find(r => r.district && r.district.includes(districtName)) || allRoutes[0]);

  tag.textContent = fullName ? fullName : `대구광역시 ${districtName} 관제 권역`;
  title.textContent = dongName ? `${districtName} ${dongName}` : (vehicle ? vehicle.name : `${districtName} 관리구역`);

  if (vehicle) {
    metrics.innerHTML = `
      <div style="font-size: 0.76rem; color: var(--accent-blue); font-weight: 700; margin-bottom: 8px;">
        🚛 권역 전담: ${vehicle.name} (${vehicle.model})
      </div>
      <div class="metric-grid">
        <div class="metric-item">
          <span class="metric-label">운행거리 단축</span>
          <strong class="metric-val text-accent">-${vehicle.improvement.distance_reduction_pct}%</strong>
          <small style="font-size: 0.62rem; color: var(--text-muted);">${vehicle.before_stats.distance_km}km → ${vehicle.after_stats.distance_km}km</small>
        </div>
        <div class="metric-item">
          <span class="metric-label">소요시간 절감</span>
          <strong class="metric-val text-accent">-${vehicle.improvement.duration_reduction_pct}%</strong>
          <small style="font-size: 0.62rem; color: var(--text-muted);">${vehicle.before_stats.duration_min}분 → ${vehicle.after_stats.duration_min}분</small>
        </div>
        <div class="metric-item">
          <span class="metric-label">PM10 저감률</span>
          <strong class="metric-val text-emerald">-${vehicle.improvement.pm10_reduction_pct}%</strong>
          <small style="font-size: 0.62rem; color: var(--text-muted);">${vehicle.before_stats.pm10_avg_after} → ${vehicle.after_stats.pm10_avg_after} ㎍/㎥</small>
        </div>
        <div class="metric-item">
          <span class="metric-label">분진 흡입 효율</span>
          <strong class="metric-val text-emerald">+${vehicle.improvement.dust_efficiency_gain_pct}%</strong>
          <small style="font-size: 0.62rem; color: var(--text-muted);">${vehicle.after_stats.dust_collected_kg}kg 포집</small>
        </div>
      </div>
      <div style="margin-top: 8px; font-size: 0.72rem; color: var(--text-muted); background: var(--bg-input); padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--bg-border); line-height: 1.4;">
        📍 <strong>관제 노선:</strong> ${route ? route.name : (dongName ? `${districtName} ${dongName} 일대 도로` : `${districtName} 주요 도로망`)}<br>
        ✨ <strong>대기 측정소:</strong> ${districtName} 대표 대기측정소(PM10) 실시간 동기화 완료
      </div>
    `;
  }

  card.style.display = 'block';
  if (window.lucide) {
    lucide.createIcons();
  }
}

function closeDetailCard() {
  const card = document.getElementById('detail-card');
  if (card) card.style.display = 'none';
}

function resetSelection() {
  selectedDistrict = null;
  selectedDongName = null;
  selectedRouteId = null;

  // 선택된 동/구 최상단 네온 하이라이트 오버레이 제거
  if (selectedDongHighlightLayer && leafletMapInstance && leafletMapInstance.hasLayer(selectedDongHighlightLayer)) {
    leafletMapInstance.removeLayer(selectedDongHighlightLayer);
    selectedDongHighlightLayer = null;
  }

  const selectEl = document.getElementById('district-filter');
  if (selectEl) selectEl.value = 'all';

  document.querySelectorAll('.district-chip').forEach(c => c.classList.remove('active'));
  closeDetailCard();

  if (leafletDongLayer) {
    leafletDongLayer.setStyle(getDongStyle);
  }

  if (leafletMapInstance && leafletRoutePolylines && leafletRoutePolylines.length > 0) {
    const allBounds = [];
    leafletRoutePolylines.forEach(p => {
      p.setStyle({ color: '#a855f7', weight: 5.2, opacity: 0.9 });
      if (p.routeData && p.routeData.points) {
        p.routeData.points.forEach(pt => allBounds.push(pt));
      }
    });
    if (allBounds.length > 0) {
      leafletMapInstance.fitBounds(allBounds, { padding: [60, 60], maxZoom: 13 });
    }
  }
}

// --------------------------------------------------------------------------
// 8. Leaflet 통합 맵 인스턴스 초기화
// --------------------------------------------------------------------------
function initRoadLeafletMap() {
  if (leafletMapInstance) {
    setTimeout(() => { leafletMapInstance.invalidateSize(); }, 200);
    return;
  }

  const mapEl = document.getElementById('map');
  if (!mapEl) return;

  // 대구 중심 좌표
  leafletMapInstance = L.map('map', {
    center: [35.8714, 128.6014],
    zoom: 12,
    zoomControl: false
  });

  // 1. 일반 도로 타일 (OpenStreetMap 기반 다크 필터, API 키 불필요)
  darkOSMTileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
    subdomains: 'abc',
    maxZoom: 19,
    className: 'map-tiles-dark'
  });

  // 2. 고해상도 위성 영상 (Esri Satellite, API 키 불필요)
  esriSatelliteTileLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics',
    maxZoom: 18
  });

  // 기본은 일반(다크) 지도로 설정
  darkOSMTileLayer.addTo(leafletMapInstance);

  // 줌 컨트롤 (우측 하단)
  L.control.zoom({ position: 'bottomright' }).addTo(leafletMapInstance);

  // 도로망 노선 레이어 그룹
  leafletRouteLayerGroup = L.featureGroup();
  leafletRoutePolylines = [];
  const allBounds = [];

  allRoutes.forEach(route => {
    if (route.points && route.points.length > 0) {
      route.points.forEach(pt => allBounds.push(pt));

      // 대기현황 색상(파랑/초록/주황/빨강)과 뚜렷이 구별되는 네온 바이올렛(#a855f7)
      const poly = L.polyline(route.points, {
        color: '#a855f7',
        weight: 5.2,
        opacity: 0.9,
        lineJoin: 'round',
        lineCap: 'round'
      });

      poly.routeData = route;

      const popupHtml = `
        <div style="min-width: 220px; font-family: inherit;">
          <div style="font-size: 0.95rem; font-weight: 700; color: #c084fc; margin-bottom: 4px;">
            ${route.name}
          </div>
          <div style="font-size: 0.78rem; color: #94a3b8; margin-bottom: 8px;">
            관리 권역: <strong style="color: #f1f5f9;">${route.district || '대구광역시'}</strong>
            ${route.length_km ? ` · ${route.length_km}km` : ''}
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: rgba(255,255,255,0.06); padding: 8px 10px; border-radius: 6px; margin-bottom: 8px;">
            <div>
              <div style="font-size: 0.68rem; color: #94a3b8;">흡입 전 미세먼지</div>
              <div style="font-size: 0.95rem; font-weight: 700; color: #f87171;">${route.pm10_before || '-'} <small style="font-size: 0.65rem;">㎍/㎥</small></div>
            </div>
            <div>
              <div style="font-size: 0.68rem; color: #94a3b8;">흡입 후 미세먼지</div>
              <div style="font-size: 0.95rem; font-weight: 700; color: #34d399;">${route.pm10_after_clean || '-'} <small style="font-size: 0.65rem;">㎍/㎥</small></div>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem;">
            <span style="color: #94a3b8;">교통 밀집도:</span>
            <span style="color: #38bdf8; font-weight: 600;">${route.traffic_level || '보통'}</span>
          </div>
        </div>
      `;

      poly.bindPopup(popupHtml);

      poly.on('mouseover', function () {
        if (isMapMouseDown || isMapDragging) return;
        this.setStyle({ color: '#ffffff', weight: 8, opacity: 1 });
      });
      poly.on('mouseout', function () {
        if (selectedRouteId) {
          if (this.routeData && this.routeData.id === selectedRouteId) {
            this.setStyle({ color: '#c084fc', weight: 8.5, opacity: 1 });
          } else {
            this.setStyle({ color: '#7e22ce', weight: 3.5, opacity: 0.35 });
          }
        } else if (selectedDistrict) {
          if (this.routeData && this.routeData.district && this.routeData.district.includes(selectedDistrict)) {
            this.setStyle({ color: '#c084fc', weight: 7.5, opacity: 1 });
          } else {
            this.setStyle({ color: '#7e22ce', weight: 4, opacity: 0.55 });
          }
        } else {
          this.setStyle({ color: '#a855f7', weight: 5.2, opacity: 0.9 });
        }
      });
      poly.on('mousedown', function (e) {
        this._mouseDownTime = Date.now();
        this._mouseDownPos = e.containerPoint;
      });
      poly.on('click', function (e) {
        const duration = Date.now() - (this._mouseDownTime || 0);
        let dist = 0;
        if (this._mouseDownPos && e.containerPoint) {
          dist = this._mouseDownPos.distanceTo(e.containerPoint);
        }
        if (isMapDragging || duration > 280 || dist > 5) {
          return;
        }
        selectedRouteId = route.id;
        if (route.district) {
          const firstDist = route.district.split('/')[0];
          selectDistrict(firstDist, route.id);
        } else {
          highlightLeafletDistrict(null, route.id);
        }
      });

      poly.addTo(leafletRouteLayerGroup);
      leafletRoutePolylines.push(poly);
    }
  });

  if (isRoutesOverlayOn) {
    leafletRouteLayerGroup.addTo(leafletMapInstance);
  }

  // 대구 전역 노선이 한눈에 들어오도록 자동 줌 맞춤
  if (allBounds.length > 0) {
    leafletMapInstance.fitBounds(allBounds, { padding: [60, 60], maxZoom: 13 });
  }

  // 지도 마우스 인터랙션 제어 (드래그/홀드 시 툴팁 및 잔여 호버 원천 차단)
  leafletMapInstance.on('mousedown', (e) => {
    isMapMouseDown = true;
    isMapDragging = false;
    mapMouseDownTime = Date.now();
    mapMouseDownPos = e.containerPoint;
    dismissAllTooltipsAndHovers();
  });

  leafletMapInstance.on('movestart dragstart', () => {
    isMapDragging = true;
    dismissAllTooltipsAndHovers();
  });

  leafletMapInstance.on('moveend dragend', () => {
    isMapMouseDown = false;
    lastDragEndTime = Date.now();
    dismissAllTooltipsAndHovers();
    setTimeout(() => {
      isMapDragging = false;
      dismissAllTooltipsAndHovers();
    }, 120);
  });

  // 지도 빈 공간 클릭 시 선택 초기화 (동 폴리곤 클릭 시에는 무시)
  leafletMapInstance.on('click', (e) => {
    if (justClickedDong) return;
    const elapsed = Date.now() - mapMouseDownTime;
    let dist = 0;
    if (mapMouseDownPos && e.containerPoint) {
      dist = mapMouseDownPos.distanceTo(e.containerPoint);
    }
    if (!isMapDragging && (Date.now() - lastDragEndTime >= 250) && elapsed < 300 && dist < 10) {
      resetSelection();
    }
  });

  // 브라우저 최상단 레벨에서 마우스 누름/뗌 즉각 포착 (이벤트 버블링 지연 완전 차단)
  window.addEventListener('mousedown', (e) => {
    if (e.button === 0) {
      isMapMouseDown = true;
      dismissAllTooltipsAndHovers();
    }
  }, true);

  window.addEventListener('mouseup', () => {
    isMapMouseDown = false;
    // lastDragEndTime은 실제 dragend 이벤트에서만 갱신 (일반 클릭 오판 방지)
    dismissAllTooltipsAndHovers();
    setTimeout(() => {
      isMapDragging = false;
      dismissAllTooltipsAndHovers();
    }, 100);
  }, true);

  // 지도 컨테이너 자체에서 마우스가 나갔을 때 툴팁 정리
  mapEl.addEventListener('mouseleave', () => {
    isMapMouseDown = false;
    isMapDragging = false;
    dismissAllTooltipsAndHovers();
  });

  setTimeout(() => {
    leafletMapInstance.invalidateSize();
  }, 250);
}

// --------------------------------------------------------------------------
// 9. 전역 이벤트 리스너 등록
// --------------------------------------------------------------------------
function setupEventListeners() {
  // 자치구 셀렉트 변경
  const districtSelect = document.getElementById('district-filter');
  if (districtSelect) {
    districtSelect.addEventListener('change', (e) => {
      const val = e.target.value;
      if (val === 'all') resetSelection();
      else selectDistrict(val);
    });
  }

  // 측정소 직접 선택 셀렉트 (좌측 패널)
  const stationSelect = document.getElementById('station-select');
  if (stationSelect) {
    stationSelect.addEventListener('change', (e) => {
      fetchAirData(e.target.value);
    });
  }

  // 모달 내 측정소 셀렉트
  const modalStationSelect = document.getElementById('modal-station-select');
  if (modalStationSelect) {
    modalStationSelect.addEventListener('change', (e) => {
      fetchAirData(e.target.value, currentAirDate);
    });
  }

  // 모달 내 조회 일자 직접 선택
  const modalDateInput = document.getElementById('modal-date-input');
  if (modalDateInput) {
    modalDateInput.addEventListener('change', (e) => {
      if (e.target.value) {
        fetchAirData(currentStationCode, e.target.value);
      }
    });
  }

  // 5분마다 실시간 대기 데이터 자동 백그라운드 갱신 (날짜가 바뀌면 자정 이후 자동 전환)
  setInterval(() => {
    // 특정 과거 날짜를 조회 중인 상태가 아니라면(실시간 모드) 최신 데이터 자동 폴링
    if (!currentAirDate) {
      fetchAirData(currentStationCode);
      fetchDistrictAirData();
    }
  }, 300000);



  // 초기화 버튼
  const resetBtn = document.getElementById('btn-reset-view');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      resetSelection();
    });
  }

  // 테마 토글 버튼
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);

      const themeIcon = document.getElementById('theme-icon');
      if (themeIcon) {
        themeIcon.setAttribute('data-lucide', newTheme === 'light' ? 'moon' : 'sun');
        lucide.createIcons();
      }
    });
  }

  // 모달 백드롭 클릭 시 닫기
  const modalBackdrop = document.getElementById('air-modal');
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', (e) => {
      if (e.target === modalBackdrop) closeAirModal();
    });
  }
}

// ==========================================================================
// 10. 전역 window 객체 명시적 함수 바인딩 (인라인 onclick & 외부 모듈 호환)
// ==========================================================================
window._realSetMasterView = setMasterView;
window.setMasterView = setMasterView;
window._realToggleNaverOverlay = toggleNaverOverlay;
window.toggleNaverOverlay = toggleNaverOverlay;
window.setNaverBaseMap = setNaverBaseMap;
window._realOpenAirModal = openAirModal;
window.openAirModal = openAirModal;
window._realCloseAirModal = closeAirModal;
window.closeAirModal = closeAirModal;
window._realCloseDetailCard = closeDetailCard;
window.closeDetailCard = closeDetailCard;
window.selectDistrict = selectDistrict;
window.selectDistrictAndDong = selectDistrictAndDong;
window.selectDong = selectDistrictAndDong;
window.resetSelection = resetSelection;
window.fetchAirData = fetchAirData;

// 대기 중인 뷰 전환 요청이 있다면 즉시 적용
if (window._pendingMasterView) {
  setMasterView(window._pendingMasterView);
}

