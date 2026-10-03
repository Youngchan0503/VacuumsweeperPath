import json
import sys
from shapely.geometry import shape

sys.stdout.reconfigure(encoding='utf-8')

with open('static/data/daegu_15_urban_zones.geojson', 'r', encoding='utf-8') as f:
    geojson = json.load(f)

print(f"=== 대구 분진흡입차량 전체 {len(geojson['features'])}개 권역 검증 ===")
for f in geojson['features']:
    p = f['properties']
    poly = shape(f['geometry'])
    c = poly.centroid
    print(f"Zone {p['zone_id']:02d}: {p['name']} | 면적: {poly.area:.5f} | 중심좌표: ({c.x:.3f}, {c.y:.3f})")
