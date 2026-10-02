import json
import math
import os

def build_daegu_dong_svg():
    # 1. vuski 동·읍 데이터 로드
    with open('scratch/daegu_dong_features.json', 'r', encoding='utf-8') as f:
        dong_fc = json.load(f)

    features = dong_fc['features']

    # 2. 바운딩 박스 계산
    all_lngs = []
    all_lats = []

    for f in features:
        geom = f['geometry']
        gtype = geom['type']
        coords = geom['coordinates']

        if gtype == 'Polygon':
            poly_list = [coords]
        elif gtype == 'MultiPolygon':
            poly_list = coords
        else:
            continue

        for poly in poly_list:
            for ring in poly:
                for pt in ring:
                    all_lngs.append(pt[0])
                    all_lats.append(pt[1])

    min_lng, max_lng = min(all_lngs), max(all_lngs)
    min_lat, max_lat = min(all_lats), max(all_lats)

    mid_lat = (min_lat + max_lat) / 2.0
    aspect = math.cos(math.radians(mid_lat))

    svg_width = 800
    svg_height = 720
    padding = 40

    draw_width = svg_width - 2 * padding
    draw_height = svg_height - 2 * padding

    lng_span = (max_lng - min_lng) * aspect
    lat_span = (max_lat - min_lat)

    scale = min(draw_width / lng_span, draw_height / lat_span)

    def project(lng, lat):
        x = padding + ((lng - min_lng) * aspect) * scale + (draw_width - lng_span * scale) / 2
        y = padding + ((max_lat - lat)) * scale + (draw_height - lat_span * scale) / 2
        return round(x, 2), round(y, 2)

    # 3. 142개 동·읍 패스 생성
    dong_paths = []
    dong_labels = []

    # 구별 색조 틴트 (시각적 구분 지원)
    district_colors = {
        '중구': '#273549',
        '동구': '#1f3044',
        '서구': '#2c3749',
        '남구': '#243b53',
        '북구': '#1d2f47',
        '수성구': '#1e3a5f',
        '달서구': '#223843',
        '달성군': '#1b2d3e'
    }

    # 주요 대표 동/읍 텍스트 라벨 (가독성을 위해 면적이 크거나 주요 거점 35개소 선별 표시)
    key_dong_labels = {
        '화원읍', '논공읍', '다사읍', '유가읍', '옥포읍', '현풍읍', '가창면', '하빈면', '구지면',
        '범어1동', '만촌1동', '지산1동', '황금1동', '고산1동',
        '성내1동', '대봉1동', '삼덕동',
        '신암1동', '신천1·2동', '효목1동', '안심1동', '불로봉무동',
        '평리1동', '비산1동', '내당1동',
        '대명1동', '이천동', '봉덕1동',
        '침산1동', '산격1동', '태전1동', '구암동', '동천동',
        '상인1동', '월성1동', '진천동', '이곡1동', '신당동', '두류1·2동'
    }

    for f in features:
        props = f['properties']
        adm_cd = props['adm_cd']
        adm_nm = props['adm_nm'] # 예: 대구광역시 수성구 범어1동
        parts = adm_nm.split()
        sggnm = props.get('sggnm', parts[1] if len(parts) > 1 else '대구')
        dong_nm = parts[-1] # 예: 범어1동, 다사읍

        geom = f['geometry']
        gtype = geom['type']
        coords = geom['coordinates']

        poly_list = [coords] if gtype == 'Polygon' else coords

        d_parts = []
        total_x = 0
        total_y = 0
        pt_count = 0

        for poly in poly_list:
            for ring in poly:
                ring_pts = []
                for pt in ring:
                    px, py = project(pt[0], pt[1])
                    ring_pts.append(f"{px} {py}")
                    total_x += px
                    total_y += py
                    pt_count += 1
                if ring_pts:
                    d_parts.append("M " + " L ".join(ring_pts) + " Z")

        d_str = " ".join(d_parts)
        path_id = f"dong_{adm_cd}"
        fill_color = district_colors.get(sggnm, '#1e293b')

        dong_paths.append(
            f'    <path id="{path_id}" class="dong-path district-{sggnm}" '
            f'data-cd="{adm_cd}" data-dong="{dong_nm}" data-district="{sggnm}" '
            f'data-fullname="{adm_nm}" style="fill: {fill_color};" d="{d_str}" />'
        )

        if pt_count > 0:
            cx = round(total_x / pt_count, 1)
            cy = round(total_y / pt_count, 1)
            
            # 주요 동/읍 라벨 텍스트
            is_key = (dong_nm in key_dong_labels) or ('읍' in dong_nm) or ('면' in dong_nm)
            text_class = "dong-label" if is_key else "dong-label-minor"
            dong_labels.append(
                f'    <text x="{cx}" y="{cy}" class="{text_class}" '
                f'data-target="{path_id}">{dong_nm}</text>'
            )

    # 4. 상세 도로망 노선 레이어 (분진흡입차량 운행 경로)
    with open('data/daegu_routes.json', 'r', encoding='utf-8') as f:
        routes_data = json.load(f)

    route_elements = []
    for r in routes_data.get('routes', []):
        pts = r.get('points', [])
        if not pts: continue
        proj_pts = [project(p[1], p[0]) for p in pts]
        d_str = 'M ' + ' L '.join(f'{x} {y}' for x, y in proj_pts)
        rid = r['id']
        name = r['name']
        dist = r.get('district', '')
        before = r.get('pm10_before', '-')
        after = r.get('pm10_after_clean', '-')

        # 1. 네온 글로우 언더레이
        route_elements.append(
            f'    <path class="route-glow-path" d="{d_str}" />'
        )
        # 2. 메인 도로 폴리라인
        route_elements.append(
            f'    <path id="svg_route_{rid}" class="route-main-path" d="{d_str}" '
            f'data-id="{rid}" data-name="{name}" data-district="{dist}" '
            f'data-before="{before}" data-after="{after}">'
            f'<title>{name} (흡입 후: {after}㎍/㎥)</title></path>'
        )
        # 3. 양 끝점 마커
        x0, y0 = proj_pts[0]
        x1, y1 = proj_pts[-1]
        route_elements.append(f'    <circle cx="{x0}" cy="{y0}" r="4.5" class="route-node" fill="#34d399" stroke="#ffffff" stroke-width="1.5" />')
        route_elements.append(f'    <circle cx="{x1}" cy="{y1}" r="4.5" class="route-node" fill="#38bdf8" stroke="#ffffff" stroke-width="1.5" />')

        # 4. 도로명 라벨 (중간 지점)
        mid_idx = len(proj_pts) // 2
        mx, my = proj_pts[mid_idx]
        sname = name.split()[0]
        route_elements.append(f'    <text x="{mx}" y="{my - 7}" class="route-name-label">{sname}</text>')

    svg_content = f'''<?xml version="1.0" encoding="utf-8"?>
<svg id="daegu-map" xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny" width="800" height="720" viewBox="0 0 800 720" stroke-linecap="round" stroke-linejoin="round">
<style>
  /* 1. 동·읍 단위 패스 스타일 */
  .dong-path {{
    stroke: rgba(255, 255, 255, 0.18);
    stroke-width: 0.8;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }}

  .dong-path:hover {{
    fill: #38bdf8 !important;
    fill-opacity: 0.95;
    stroke: #0284c7;
    stroke-width: 2.0;
    filter: drop-shadow(0 4px 10px rgba(56, 189, 248, 0.5));
  }}

  .dong-path.selected {{
    fill: #10b981 !important;
    fill-opacity: 0.95;
    stroke: #059669;
    stroke-width: 2.4;
    filter: drop-shadow(0 6px 14px rgba(16, 185, 129, 0.6));
  }}

  /* 자치구 필터링 시 해당 구의 동들 하이라이트 */
  .dong-path.highlight-district {{
    stroke: rgba(56, 189, 248, 0.6);
    stroke-width: 1.5;
  }}

  /* 2. 동·읍 텍스트 라벨 */
  text.dong-label {{
    fill: #f8fafc;
    font-family: 'Pretendard', -apple-system, sans-serif;
    font-size: 11px;
    font-weight: 700;
    pointer-events: none;
    text-anchor: middle;
    paint-order: stroke;
    stroke: #0f172a;
    stroke-width: 2.5px;
    stroke-linejoin: miter;
    user-select: none;
  }}

  text.dong-label-minor {{
    display: none; /* 세부 동 라벨은 줌 또는 호버 시 연동 */
    fill: #94a3b8;
    font-family: 'Pretendard', sans-serif;
    font-size: 9px;
    text-anchor: middle;
    pointer-events: none;
  }}

  /* 3. 분진흡입차량 상세 도로망 통합 노선 스타일 */
  .route-glow-path {{
    fill: none;
    stroke: rgba(16, 185, 129, 0.4);
    stroke-width: 9px;
    stroke-linecap: round;
    stroke-linejoin: round;
    filter: drop-shadow(0 0 6px #10b981);
    pointer-events: none;
  }}

  .route-main-path {{
    fill: none;
    stroke: #10b981;
    stroke-width: 4px;
    stroke-linecap: round;
    stroke-linejoin: round;
    cursor: pointer;
    transition: all 0.2s ease;
  }}

  .route-main-path:hover {{
    stroke: #38bdf8;
    stroke-width: 7px;
    filter: drop-shadow(0 0 12px #38bdf8);
  }}

  .route-node {{
    filter: drop-shadow(0 0 4px rgba(16, 185, 129, 0.8));
    pointer-events: none;
  }}

  text.route-name-label {{
    fill: #34d399;
    font-family: 'Pretendard', -apple-system, sans-serif;
    font-size: 11px;
    font-weight: 800;
    text-anchor: middle;
    paint-order: stroke;
    stroke: #0b0f19;
    stroke-width: 3.5px;
    pointer-events: none;
  }}

  /* Light Theme 대응 */
  [data-theme="light"] .dong-path {{
    stroke: rgba(0, 0, 0, 0.15);
  }}
  [data-theme="light"] .dong-path:hover {{
    fill: #7dd3fc !important;
    stroke: #0284c7;
  }}
  [data-theme="light"] .dong-path.selected {{
    fill: #34d399 !important;
    stroke: #059669;
  }}
  [data-theme="light"] text.dong-label {{
    fill: #0f172a;
    stroke: #ffffff;
  }}
  [data-theme="light"] text.route-name-label {{
    stroke: #ffffff;
  }}
</style>

<g id="daegu-dong-map">
  <!-- 1. 142개 동·읍·면 벡터 레이어 (대구 행정구역) -->
  <g id="daegu-dongs">
{chr(10).join(dong_paths)}
  </g>

  <!-- 2. 동·읍 텍스트 라벨 레이어 -->
  <g id="daegu-labels">
{chr(10).join(dong_labels)}
  </g>

  <!-- 3. 상세 도로망 통합 노선 레이어 (분진흡입차량 운행 경로) -->
  <g id="daegu-routes">
{chr(10).join(route_elements)}
  </g>
</g>
</svg>
'''
    return svg_content

if __name__ == '__main__':
    content = build_daegu_dong_svg()
    
    # 1. static/img/daegu-dong-map.svg 저장
    with open('static/img/daegu-dong-map.svg', 'w', encoding='utf-8') as f:
        f.write(content)
        
    # 2. data/daegu-dong-map.svg 저장
    with open('data/daegu-dong-map.svg', 'w', encoding='utf-8') as f:
        f.write(content)

    # 3. 메인 daegu-map.svg 도 동·읍 분할 지도로 교체!
    with open('static/img/daegu-map.svg', 'w', encoding='utf-8') as f:
        f.write(content)
    with open('data/daegu-map.svg', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Successfully built daegu-dong-map.svg and updated daegu-map.svg!")
