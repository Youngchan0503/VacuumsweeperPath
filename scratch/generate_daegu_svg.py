import json
import math
import urllib.request
import os

def generate_daegu_svg():
    url = 'https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea-municipalities-2018-geo.json'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    raw = urllib.request.urlopen(req, timeout=15).read()
    geo_data = json.loads(raw)

    # 대구 8개 구·군 추출 (22010 ~ 22310)
    # 영어 id 매핑 및 한글 이름 매핑
    name_map = {
        '22010': {'id': 'junggu', 'name': '중구', 'name_eng': 'Jung-gu'},
        '22020': {'id': 'donggu', 'name': '동구', 'name_eng': 'Dong-gu'},
        '22030': {'id': 'seogu', 'name': '서구', 'name_eng': 'Seo-gu'},
        '22040': {'id': 'namgu', 'name': '남구', 'name_eng': 'Nam-gu'},
        '22050': {'id': 'bukgu', 'name': '북구', 'name_eng': 'Buk-gu'},
        '22060': {'id': 'suseonggu', 'name': '수성구', 'name_eng': 'Suseong-gu'},
        '22070': {'id': 'dalseogu', 'name': '달서구', 'name_eng': 'Dalseo-gu'},
        '22310': {'id': 'dalseonggun', 'name': '달성군', 'name_eng': 'Dalseong-gun'}
    }

    daegu_features = [f for f in geo_data['features'] if f['properties']['code'] in name_map]

    # 전체 바운딩 박스 계산
    all_lngs = []
    all_lats = []
    for f in daegu_features:
        coords = f['geometry']['coordinates']
        # MultiPolygon: [ [ [ [lng, lat], ... ] ] ]
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    all_lngs.append(pt[0])
                    all_lats.append(pt[1])

    min_lng, max_lng = min(all_lngs), max(all_lngs)
    min_lat, max_lat = min(all_lats), max(all_lats)

    mid_lat = (min_lat + max_lat) / 2.0
    aspect = math.cos(math.radians(mid_lat))

    # SVG 뷰포트 크기 및 여백
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

    paths_xml = []
    texts_xml = []

    # 각 구·군 텍스트 라벨 미세 조정 오프셋 (겹침 방지 및 가독성 최적화)
    label_offsets = {
        'junggu': (0, 0),
        'donggu': (15, -10),
        'seogu': (0, 0),
        'namgu': (0, 5),
        'bukgu': (0, -10),
        'suseonggu': (10, 0),
        'dalseogu': (0, 0),
        'dalseonggun': (-20, 30) # 달성군 남부 중심
    }

    for f in daegu_features:
        code = f['properties']['code']
        info = name_map[code]
        poly_d_list = []

        total_x = 0
        total_y = 0
        pt_count = 0

        coords = f['geometry']['coordinates']
        for poly in coords:
            for ring in poly:
                ring_points = []
                for pt in ring:
                    px, py = project(pt[0], pt[1])
                    ring_points.append(f"{px} {py}")
                    total_x += px
                    total_y += py
                    pt_count += 1
                poly_d_list.append("M " + " L ".join(ring_points) + " Z")

        d_str = " ".join(poly_d_list)
        path_id = info['id']
        name_kor = info['name']

        paths_xml.append(f'  <path id="{path_id}" data-name="{name_kor}" d="{d_str}" />')

        # 라벨 중심점 계산
        # 달서구/달성군 등 폴리곤이 나뉜 경우 적절한 위치 선정
        center_x = round(total_x / pt_count, 1)
        center_y = round(total_y / pt_count, 1)

        # 특수 보정
        if path_id == 'junggu':
            # 중구는 서구, 남구, 북구, 동구 사이에 작게 위치하므로 약간 조정
            center_x += 0
            center_y += 0
        elif path_id == 'dalseonggun':
            # 달성군은 논공/현풍 쪽이 면적이 크므로
            center_x -= 15
            center_y += 40

        dx, dy = label_offsets.get(path_id, (0, 0))
        tx = center_x + dx
        ty = center_y + dy

        texts_xml.append(f'  <text x="{tx}" y="{ty}" data-target="{path_id}">{name_kor}</text>')

    svg_content = f'''<?xml version="1.0" encoding="utf-8"?>
<svg id="daegu-map" xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny" width="800" height="720" viewBox="0 0 800 720" stroke-linecap="round" stroke-linejoin="round">
<style>
  path {{
    fill: #1e293b;
    stroke: #475569;
    stroke-width: 1.5;
    cursor: pointer;
    transition: all 0.25s ease-in-out;
  }}

  path:hover {{
    fill: #38bdf8;
    fill-opacity: 0.85;
    stroke: #0284c7;
    stroke-width: 2.5;
    filter: drop-shadow(0 4px 12px rgba(56, 189, 248, 0.4));
  }}

  path.selected {{
    fill: #10b981 !important;
    fill-opacity: 0.9;
    stroke: #059669;
    stroke-width: 3;
    filter: drop-shadow(0 6px 16px rgba(16, 185, 129, 0.5));
  }}

  text {{
    fill: #f8fafc;
    font-family: 'Pretendard', -apple-system, sans-serif;
    font-size: 14px;
    font-weight: 700;
    pointer-events: none;
    text-anchor: middle;
    paint-order: stroke;
    stroke: #0f172a;
    stroke-width: 3px;
    stroke-linecap: butt;
    stroke-linejoin: miter;
    user-select: none;
  }}

  /* Light Theme 호환 */
  [data-theme="light"] path {{
    fill: #f1f5f9;
    stroke: #94a3b8;
  }}
  [data-theme="light"] path:hover {{
    fill: #bae6fd;
    stroke: #0284c7;
  }}
  [data-theme="light"] path.selected {{
    fill: #34d399 !important;
    stroke: #059669;
  }}
  [data-theme="light"] text {{
    fill: #0f172a;
    stroke: #ffffff;
  }}
</style>
<g id="daegu-districts">
{chr(10).join(paths_xml)}
{chr(10).join(texts_xml)}
</g>
</svg>
'''
    return svg_content

if __name__ == '__main__':
    content = generate_daegu_svg()
    
    # 1. static/img/daegu-map.svg 저장
    os.makedirs('static/img', exist_ok=True)
    with open('static/img/daegu-map.svg', 'w', encoding='utf-8') as f:
        f.write(content)
        
    # 2. data/daegu-map.svg 에도 저장 (gyungnam-map.svg와 동일한 위치)
    with open('data/daegu-map.svg', 'w', encoding='utf-8') as f:
        f.write(content)

    print("daegu-map.svg generated successfully!")
