import json
import sys
from shapely.geometry import shape, mapping, Polygon, MultiPolygon, Point
from shapely.ops import unary_union

sys.stdout.reconfigure(encoding='utf-8')

with open("static/data/daegu_dong.geojson", "r", encoding="utf-8") as f:
    dong_geojson = json.load(f)

# Test Zone 8 features
zone8_polys = []
for feat in dong_geojson['features']:
    p = feat['properties']
    if p.get('district') == '달서구' and any(kw in p.get('dong', '') for kw in ['월성', '진천', '상인', '유천', '대곡', '도원', '본리', '본동', '송현', '감삼', '두류', '성당', '죽전']):
        poly = shape(feat['geometry'])
        if not poly.is_valid:
            poly = poly.buffer(0)
        zone8_polys.append(poly)

zone8_full = unary_union(zone8_polys)

# Correct Mountain Exclusion Polygon for Cheongryongsan / Sampilbong / Beomdugolsan / Yaksangolsan
# High mountain massif strictly south of lat 35.795
# Covers the entire mountain tail to lon 128.585 (eliminating floating orange shards)
CHEONGRYONGSAN_MOUNTAIN = Polygon([
    [128.500, 35.740], [128.505, 35.792], [128.520, 35.795], [128.540, 35.792],
    [128.558, 35.790], [128.585, 35.795], [128.588, 35.740], [128.540, 35.730],
    [128.500, 35.740]
])

zone8_urban = zone8_full.difference(CHEONGRYONGSAN_MOUNTAIN)

# Test residential points in Daegok 2nd District & Dowon-dong (MUST BE TRUE)
residential_points = [
    ('상화로 / 진천역 방면', 128.530, 35.818),
    ('대곡2지구 한실초 / 한실로 중심 (스크린샷 상단 도심)', 128.530, 35.810),
    ('대곡2지구 갈밭로 / 갈밭남로 (스크린샷 중앙 주거지)', 128.525, 35.805),
    ('도원동 월광수변공원 / 도원지 북측 진입로', 128.548, 35.808),
    ('대곡역 배후 주거단지 / 대곡동', 128.515, 35.812),
    ('상인동 롯데백화점 / 월곡로', 128.540, 35.820)
]

# Test mountain points (MUST BE FALSE / EXCLUDED)
mountain_points = [
    ('청룡산 정상 (794m - 스크린샷 우하단 산지)', 128.575, 35.770),
    ('이필봉 정상 (421m - 스크린샷 중앙 산림)', 128.540, 35.775),
    ('약산골산 (314m - 스크린샷 하단 산림)', 128.525, 35.765),
    ('범두골산 (481m - 스크린샷 남측 산림)', 128.545, 35.760)
]

print("=== [대곡2지구 / 한실로 / 갈밭로 도심 포함 검증] ===")
all_city_ok = True
for name, lon, lat in residential_points:
    pt = Point(lon, lat)
    inside = zone8_urban.contains(pt)
    print(f"{'[OK]' if inside else '[FAIL]'} {name} ({lon}, {lat}) -> 포함: {inside}")
    if not inside: all_city_ok = False

print("\n=== [청룡산 / 이필봉 / 범두골산 고지대 산림 제외 검증] ===")
all_mountain_ok = True
for name, lon, lat in mountain_points:
    pt = Point(lon, lat)
    inside = zone8_urban.contains(pt)
    print(f"{'[OK]' if not inside else '[FAIL]'} {name} ({lon}, {lat}) -> 제외됨: {not inside}")
    if inside: all_mountain_ok = False

print(f"\n결과: {'완벽 검증 완료 ✓' if all_city_ok and all_mountain_ok else '조정 필요'}")
