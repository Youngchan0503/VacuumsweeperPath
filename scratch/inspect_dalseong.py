import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/data/daegu_dong.geojson', 'r', encoding='utf-8') as f:
    d = json.load(f)

for feat in d['features']:
    p = feat['properties']
    if p.get('district') == '달성군':
        print(f"dong: '{p.get('dong')}', adm_nm: '{p.get('adm_nm')}', temp: '{p.get('temp')}'")
