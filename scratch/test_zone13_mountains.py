import json
import sys
from shapely.geometry import shape, mapping, Polygon, MultiPolygon, Point
from shapely.ops import unary_union

sys.stdout.reconfigure(encoding='utf-8')

with open("static/data/daegu_dong.geojson", "r", encoding="utf-8") as f:
    dong_geojson = json.load(f)

# Zone 13 dongs
zone13_polys = []
for feat in dong_geojson['features']:
    p = feat['properties']
    if p.get('district') == '달성군' and p.get('dong') in ['유가읍', '구지면', '현풍읍', '논공읍', '옥포읍']:
        poly = shape(feat['geometry'])
        if not poly.is_valid:
            poly = poly.buffer(0)
        zone13_polys.append(poly)

zone13_full = unary_union(zone13_polys)
print(f"Zone 13 total area: {zone13_full.area:.6f}")

# Mountain exclusion polygons specifically for Zone 13
ZONE13_MOUNTAINS = [
    # 1. 비슬산 주능선 및 동측 산악지대 (유가/현풍/논공/옥포 동측의 거대한 비슬산림)
    # DGIST(128.468), 테크노폴리스(128.46~128.48), 현풍도심(128.44~128.46)은 보존
    Polygon([
        [128.482, 35.630], [128.485, 35.660], [128.480, 35.690], [128.482, 35.710],
        [128.490, 35.730], [128.500, 35.760], [128.520, 35.780], [128.550, 35.780],
        [128.600, 35.750], [128.580, 35.630], [128.482, 35.630]
    ]),

    # 2. 금계산 / 노이리·상리·하리 중앙 산림 (옥포 강림/교항 서측과 논공 달성산단 동측 사이의 순수 산지)
    Polygon([
        [128.460, 35.760], [128.475, 35.765], [128.480, 35.775], [128.475, 35.785],
        [128.462, 35.785], [128.455, 35.770], [128.460, 35.760]
    ]),

    # 3. 대니산 산림 (구지면 자모리/오설리/오산리 및 현풍 서측 산지)
    # 국가산단(128.40~128.43, 35.64~35.67) 및 구지면사무소/창리 보존
    Polygon([
        [128.395, 35.680], [128.420, 35.685], [128.440, 35.700], [128.435, 35.720],
        [128.405, 35.715], [128.385, 35.695], [128.395, 35.680]
    ]),

    # 4. 옥포 기세리/용연사/반송리 동측 깊은 산림 (옥포 강림리 도심 동측 순수 산악지대)
    Polygon([
        [128.510, 35.775], [128.530, 35.775], [128.560, 35.800], [128.530, 35.815],
        [128.512, 35.800], [128.510, 35.775]
    ])
]

zone13_mountains_union = unary_union(ZONE13_MOUNTAINS)

zone13_urban = zone13_full.difference(zone13_mountains_union)
print(f"Zone 13 urban area after mountain exclusion: {zone13_urban.area:.6f} (Reduced by {(1 - zone13_urban.area/zone13_full.area)*100:.1f}%)")

# Test key urban areas in Zone 13 are INSIDE
test_points = [
    ('유가 테크노폴리스 상업지구 (봉리)', 128.465, 35.692),
    ('유가 DGIST/테크노폴리스 (상리)', 128.468, 35.700),
    ('현풍읍 행정복지센터/현풍도심', 128.445, 35.705),
    ('구지 대구국가산단 1단계 (창리)', 128.410, 35.660),
    ('구지 대구국가산단 2단계 (예현리)', 128.430, 35.645),
    ('구지 국가산단 주거지구 (응암리)', 128.405, 35.655),
    ('논공 달성1차산업단지 (남리)', 128.445, 35.748),
    ('논공읍 행정복지센터 (북리)', 128.440, 35.760),
    ('옥포 대구옥포천년나무/교항리', 128.485, 35.790),
    ('옥포읍 행정복지센터 (강림리)', 128.490, 35.785)
]

# Test mountain areas in Zone 13 are OUTSIDE (Excluded)
mountain_test_points = [
    ('비슬산 대견봉/천왕봉 (유가 동측)', 128.520, 35.690),
    ('비슬산 유가사 계곡부 (양리/용리 동측)', 128.505, 35.680),
    ('최정산 서남릉 (논공/옥포 동측)', 128.540, 35.740),
    ('대니산 정상 (구지/현풍 서측)', 128.415, 35.700),
    ('금계산 정상 (논공/옥포 중앙)', 128.475, 35.775)
]

print("\n--- [도심 포함 여부 검증] ---")
for name, lon, lat in test_points:
    pt = Point(lon, lat)
    print(f"{'[OK]' if zone13_urban.contains(pt) else '[FAIL]'} {name} -> 포함: {zone13_urban.contains(pt)}")

print("\n--- [산림 제외 여부 검증] ---")
for name, lon, lat in mountain_test_points:
    pt = Point(lon, lat)
    print(f"{'[OK]' if not zone13_urban.contains(pt) else '[FAIL]'} {name} -> 제외됨: {not zone13_urban.contains(pt)}")
