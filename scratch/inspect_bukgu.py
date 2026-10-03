import json
import sys
from shapely.geometry import shape

sys.stdout.reconfigure(encoding='utf-8')

with open('static/data/daegu_dong.geojson', 'r', encoding='utf-8') as f:
    d = json.load(f)

print("=== 북구의 모든 행정동 목록 및 위치 ===")
for feat in d['features']:
    p = feat['properties']
    if p.get('district') == '북구':
        poly = shape(feat['geometry'])
        c = poly.centroid
        print(f"동: '{p.get('dong')}', adm_nm: '{p.get('adm_nm')}', 중심: ({c.x:.3f}, {c.y:.3f})")
