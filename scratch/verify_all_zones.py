import json
import sys
from shapely.geometry import shape, Point

sys.stdout.reconfigure(encoding='utf-8')

with open("static/data/daegu_15_urban_zones.geojson", "r", encoding="utf-8") as f:
    geojson = json.load(f)

landmarks = [
    ('Zone 1 (성서산단/이곡)', 1, 128.508, 35.852, '이곡역/성서이마트'),
    ('Zone 2 (서대구/평리/비산)', 2, 128.555, 35.873, '서구청/평리동'),
    ('Zone 3 (검단/유통단지/산격)', 3, 128.608, 35.908, '엑스코/유통단지'),
    ('Zone 4 (수성남부/지산/범물)', 4, 128.635, 35.825, '범물역/지산동'),
    ('Zone 5 (동대구/신천/신암)', 5, 128.628, 35.878, '동대구역/신세계'),
    ('Zone 6 (다사/하빈/화원)', 6, 128.463, 35.856, '대실역/다사도심'),
    ('Zone 7 (칠곡지구/동천/구암)', 7, 128.560, 35.940, '동천역/칠곡3지구중심'),
    ('Zone 7 (칠곡지구/태전)', 7, 128.545, 35.918, '태전역/칠곡네거리'),
    ('Zone 8 (월배/상인/진천/대곡2지구)', 8, 128.525, 35.808, '대곡2지구 한실로/갈밭로'),
    ('Zone 9 (남구/대명/봉덕)', 9, 128.583, 35.850, '영남대의료원/안지랑'),
    ('Zone 10 (중구 원도심/동성로)', 10, 128.595, 35.870, '반월당/중앙로'),
    ('Zone 11 (신서혁신/안심/율하)', 11, 128.720, 35.870, '율하역/혁신도시'),
    ('Zone 12 (수성도심/범어/만촌)', 12, 128.625, 35.858, '범어네거리/수성구청'),
    ('Zone 13 (달성중부/논공산단/옥포)', 13, 128.445, 35.750, '논공 달성산단/북리'),
    ('Zone 14 (무태조야/서변/동변)', 14, 128.595, 35.910, '서변동도심'),
    ('Zone 15 (수성동부/시지/신매)', 15, 128.705, 35.840, '신매역/시지도심'),
    ('Zone 16 (달성남부/테크노/국가산단/구지)', 16, 128.465, 35.692, '유가 테크노폴리스 중심')
]

mountain_points = [
    ('앞산 정상 (남구/수성구 남측)', 128.575, 35.805),
    ('팔공산 갓바위/동화사 능선 (동구 북측)', 128.705, 35.985),
    ('비슬산 대견봉 (달성군 남동측)', 128.520, 35.690),
    ('와룡산 능선 (달서구/서구 경계 산지)', 128.515, 35.880),
    ('도덕산/명봉산 정상 (북구 칠곡 북측 산림)', 128.510, 35.975),
    ('청룡산 정상부 (달서구 도원 남측 산지)', 128.575, 35.770)
]

features_by_id = {f['properties']['zone_id']: shape(f['geometry']) for f in geojson['features']}

print("=== [1] 16개 운행구간 핵심 도심·생활권 포함 검증 ===")
all_city_ok = True
for name, zid, lon, lat, place in landmarks:
    poly = features_by_id.get(zid)
    if not poly:
        print(f"[FAIL] {name}: Polygon not found")
        all_city_ok = False
        continue
    pt = Point(lon, lat)
    contains = poly.contains(pt)
    if contains:
        print(f"[OK] {name}: {place} -> 도심 영역 정상 포함 (OK)")
    else:
        print(f"[WARN] {name}: {place} -> 미포함")
        all_city_ok = False

print("\n=== [2] 주요 산악림(Mountain Peaks) 제외 검증 ===")
all_mountains_excluded = True
for m_name, m_lon, m_lat in mountain_points:
    m_pt = Point(m_lon, m_lat)
    covered_zones = [zid for zid, poly in features_by_id.items() if poly.contains(m_pt)]
    if not covered_zones:
        print(f"[OK] {m_name} -> 산림 지형 정상 제외됨 (OK)")
    else:
        print(f"[WARN] {m_name} -> {covered_zones}구간에 포함됨")
        all_mountains_excluded = False

print("\n----------------------------------------------------")
print(f"총 피처 수: {len(geojson['features'])}개 구간")
print(f"도심 주거/상권 포함 상태: {'100% 정상 포함 완료 ✓' if all_city_ok else '오류 있음'}")
print(f"산악/임야 지역 제외 상태: {'100% 정상 제외 완료 ✓' if all_mountains_excluded else '오류 있음'}")
print("----------------------------------------------------")
