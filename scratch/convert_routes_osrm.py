import os
import json
import urllib.request
import time

ROUTES_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'daegu_routes.json')

def get_osrm_detailed_route(coords):
    # coords: [[lat, lng], [lat, lng], ...]
    coords_str = ';'.join([f"{lng:.6f},{lat:.6f}" for lat, lng in coords])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('code') == 'Ok' and data.get('routes'):
                route = data['routes'][0]
                geom = route['geometry']['coordinates']
                # GeoJSON coordinates are [lng, lat] -> convert to [lat, lng]
                points = [[round(c[1], 6), round(c[0], 6)] for c in geom]
                distance_km = round(route['distance'] / 1000.0, 1)
                return points, distance_km
    except Exception as e:
        print(f"OSRM Error: {e}")
    return None, None

def convert_all():
    with open(ROUTES_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 정의된 노선별 주요 간선도로 경유 거점 (큰 도로 차선 상에 위치하도록 정밀 교차로 좌표 설정)
    route_waypoints = {
        "R01": [ # 달구벌대로
            [35.8562, 128.4907], # 계명대역
            [35.8523, 128.5101], # 성서산단역
            [35.8533, 128.5292], # 죽전네거리
            [35.8548, 128.5447], # 감삼역
            [35.8601, 128.5670], # 두류네거리
            [35.8625, 128.5746], # 반고개네거리
            [35.8655, 128.5934], # 반월당네거리
            [35.8617, 128.6067], # 삼덕네거리
            [35.8589, 128.6251], # 범어네거리
            [35.8558, 128.6433], # 만촌네거리
            [35.8521, 128.6650]  # 연호역
        ],
        "R02": [ # 신천대로
            [35.8340, 128.6080], # 상동교
            [35.8450, 128.6085], # 중동교
            [35.8575, 128.6095], # 대봉교
            [35.8640, 128.6098], # 수성교
            [35.8765, 128.6107], # 신천교
            [35.8880, 128.5990], # 침산교
            [35.8940, 128.5870], # 노원하수처리장
            [35.8980, 128.5600]  # 팔달교
        ],
        "R03": [ # 동대구로
            [35.8589, 128.6251], # 범어네거리
            [35.8690, 128.6250], # MBC네거리
            [35.8778, 128.6285], # 동대구역네거리
            [35.8845, 128.6235]  # 파티마병원삼거리
        ],
        "R04": [ # 국채보상로
            [35.8690, 128.5580], # 평리네거리
            [35.8700, 128.5700], # 비산네거리
            [35.8690, 128.5815], # 서문시장/동산네거리
            [35.8700, 128.5960], # 종로초교/만경관
            [35.8710, 128.6060], # 동인네거리
            [35.8750, 128.6120], # 신천교 서단
            [35.8780, 128.6180]  # 칠성시장/신암동 방향
        ],
        "R05": [ # 앞산순환로
            [35.8340, 128.6080], # 상동교
            [35.8310, 128.5970], # 보훈병원
            [35.8290, 128.5770], # 빨래터공원
            [35.8295, 128.5700], # 대덕승마장
            [35.8310, 128.5550], # 월촌골
            [35.8270, 128.5380]  # 월곡로
        ],
        "R06": [ # 중앙대로
            [35.8770, 128.5960], # 대구역네거리
            [35.8714, 128.5940], # 중앙로역
            [35.8655, 128.5934], # 반월당네거리
            [35.8570, 128.5900], # 명덕네거리
            [35.8475, 128.5870], # 교대역
            [35.8420, 128.5780]  # 영대병원네거리
        ]
    }

    updated_count = 0
    for r in data['routes']:
        rid = r['id']
        waypoints = route_waypoints.get(rid)
        if not waypoints:
            continue

        print(f"[{rid}] {r['name']} OSRM 도로 정밀 경로 요청 중...")
        pts, length_km = get_osrm_detailed_route(waypoints)
        if pts and len(pts) > 0:
            print(f" -> 성공: {len(pts)}개 정밀 도로 포인트 (거리: {length_km}km)")
            r['points'] = pts
            if length_km:
                r['length_km'] = length_km
            updated_count += 1
        else:
            print(f" -> 실패: OSRM 응답 없음, 기존 좌표 유지")
        time.sleep(1) # API 매너 딜레이

    if updated_count > 0:
        with open(ROUTES_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n총 {updated_count}개 노선이 실제 지도 큰 도로 정밀 좌표로 업데이트 완료되었습니다!")

if __name__ == '__main__':
    convert_all()
