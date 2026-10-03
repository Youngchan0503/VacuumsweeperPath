import json
from shapely.geometry import shape, mapping, LineString, MultiLineString, Polygon, MultiPolygon, Point
from shapely.ops import unary_union

# 1. Load dong geojson
with open("static/data/daegu_dong.geojson", "r", encoding="utf-8") as f:
    dong_geojson = json.load(f)

# 2. Load OSM roads from scratch/roads_raw.json (4,033 drivable roads)
with open(r"C:\Users\lgiht\.gemini\antigravity-ide\brain\73d9d0cc-daab-497b-a22a-b6c7d1d0d0ba\scratch\roads_raw.json", "r", encoding="utf-8") as f:
    roads_raw = json.load(f)

road_lines = []
for elem in roads_raw.get("elements", []):
    if "geometry" in elem:
        coords = [(pt["lon"], pt["lat"]) for pt in elem["geometry"]]
        if len(coords) >= 2:
            road_lines.append(LineString(coords))

# ~350m buffer along all major roads
roads_buffered = unary_union([line.buffer(0.0032, resolution=4) for line in road_lines])

# 3. Define purely uninhabited mountain peaks / core ridgeline exclusion masks (산 정상/능선 거대 암벽/원시림)
CORE_MOUNTAIN_PEAKS = [
    # 비슬산 대견봉/조화봉/월광봉 정상부 산림 (달성군 동측 능선)
    Polygon([
        [128.505, 35.670], [128.535, 35.680], [128.545, 35.710], [128.570, 35.730],
        [128.595, 35.720], [128.575, 35.660], [128.530, 35.640], [128.505, 35.670]
    ]),
    # 와룡산 정상 능선부 (달서구/서구 경계 산림)
    Polygon([
        [128.505, 35.870], [128.520, 35.875], [128.532, 35.885], [128.525, 35.895],
        [128.505, 35.892], [128.498, 35.880], [128.505, 35.870]
    ]),
    # 앞산/대덕산 정상부 (남구/수성구 남측 암벽/산림)
    Polygon([
        [128.555, 35.825], [128.575, 35.828], [128.605, 35.822], [128.615, 35.805],
        [128.575, 35.790], [128.550, 35.805], [128.555, 35.825]
    ]),
    # 팔공산 정상부 능선 (동구 북측 국립공원)
    Polygon([
        [128.630, 35.960], [128.680, 35.960], [128.730, 35.975], [128.760, 36.010],
        [128.650, 36.030], [128.600, 35.980], [128.630, 35.960]
    ])
]
core_peaks_union = unary_union(CORE_MOUNTAIN_PEAKS)

zones_def = [
  {'id': 1, 'name': '1구간 (성서산단·이곡)', 'matchDistricts': ['달서구'], 'matchKeywords': ['신당', '이곡', '호림', '갈산', '파호', '대천', '월암', '용산', '장기', '장동']},
  {'id': 2, 'name': '2구간 (서대구산단·평리·비산·내당)', 'matchDistricts': ['서구'], 'matchKeywords': ['이현', '평리', '비산', '원대', '상중이', '내당']},
  {'id': 3, 'name': '3구간 (검단·공항·유통단지·산격)', 'matchDistricts': ['북구', '동구'], 'matchKeywords': ['산격', '복현', '검단', '불로', '봉무', '지저', '공산']},
  {'id': 4, 'name': '4구간 (수성남부·지산·범물·두산·파동)', 'matchDistricts': ['수성구'], 'matchKeywords': ['지산', '범물', '황금', '두산', '상동', '중동', '파동']},
  {'id': 5, 'name': '5구간 (동대구도심·신천·신암·효목)', 'matchDistricts': ['동구'], 'matchKeywords': ['신천', '신암', '효목']},
  {'id': 6, 'name': '6구간 (다사·하빈·화원)', 'matchDistricts': ['달성군'], 'matchKeywords': ['다사', '하빈', '화원']},
  {'id': 7, 'name': '7구간 (칠곡지구·태전·구암·관음·국우)', 'matchDistricts': ['북구'], 'matchKeywords': ['태전', '구암', '관음', '읍내', '동천', '국우', '학정', '관문']},
  {'id': 8, 'name': '8구간 (월배·상인·도원·송현·두류)', 'matchDistricts': ['달서구'], 'matchKeywords': ['월성', '진천', '상인', '유천', '대곡', '도원', '본리', '본동', '송현', '감삼', '두류', '성당', '죽전']},
  {'id': 9, 'name': '9구간 (남구전역·대명·봉덕·이천)', 'matchDistricts': ['남구'], 'matchKeywords': ['대명', '봉덕', '이천']},
  {'id': 10, 'name': '10구간 (중구 원도심·침산·노원·칠성)', 'matchDistricts': ['중구', '북구'], 'matchKeywords': ['동인', '삼덕', '성내', '대신', '남산', '대봉', '칠성', '침산', '고성', '노원', '대현']},
  {'id': 11, 'name': '11구간 (신서혁신·안심·율하)', 'matchDistricts': ['동구'], 'matchKeywords': ['율하', '동호', '신서', '서호', '각산', '안심', '혁신', '동촌', '방촌', '해안', '도평']},
  {'id': 12, 'name': '12구간 (수성도심·범어·만촌·수성동)', 'matchDistricts': ['수성구'], 'matchKeywords': ['범어', '만촌', '수성']},
  {'id': 13, 'name': '13구간 (달성 테크노·국가산단·현풍·논공·옥포)', 'matchDistricts': ['달성군'], 'matchKeywords': ['유가', '구지', '현풍', '논공', '옥포']},
  {'id': 14, 'name': '14구간 (서변·동변·연경·도남·무태조야)', 'matchDistricts': ['북구'], 'matchKeywords': ['서변', '동변', '연경', '도남', '무태조야']},
  {'id': 15, 'name': '15구간 (수성동부·시지·신매·사월·알파시티)', 'matchDistricts': ['수성구'], 'matchKeywords': ['고산', '시지', '신매', '사월', '매호', '가천', '삼덕', '연호', '이천', '노변', '대구알파시티', '욱수']}
]

def find_zone(dist, dong):
    dist = (dist or '').strip()
    dong = (dong or '').strip()
    if dong == '가창면': return None
    for z in zones_def:
        if dist in z['matchDistricts'] and any(kw in dong for kw in z['matchKeywords']):
            return z
    return None

zone_features = []

for z in zones_def:
    zone_id = z['id']
    polys = []
    
    for feat in dong_geojson['features']:
        props = feat['properties']
        dist = props.get('district', '')
        dong = props.get('dong', '')
        matched = find_zone(dist, dong)
        if matched and matched['id'] == zone_id:
            poly = shape(feat['geometry'])
            if not poly.is_valid:
                poly = poly.buffer(0)
            polys.append(poly)
            
    if not polys:
        continue
        
    zone_full_geom = unary_union(polys)
    
    # 1. Intersect with the road & living area buffer
    urban_geom = zone_full_geom.intersection(roads_buffered)
    
    # 2. Subtract uninhabited core mountain peaks
    urban_geom = urban_geom.difference(core_peaks_union)
    
    if urban_geom.is_empty:
        urban_geom = zone_full_geom
    else:
        urban_geom = urban_geom.buffer(0.0010).buffer(-0.0006)
        
    urban_geom_simplified = urban_geom.simplify(0.00008, preserve_topology=True)
    
    feature = {
        "type": "Feature",
        "properties": {
            "zone_id": zone_id,
            "zone_code": f"Z{zone_id:02d}",
            "name": z['name'],
            "urban_only": True
        },
        "geometry": mapping(urban_geom_simplified)
    }
    zone_features.append(feature)

output_geojson = {
    "type": "FeatureCollection",
    "features": zone_features
}

output_path = "static/data/daegu_15_urban_zones.geojson"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output_geojson, f, ensure_ascii=False)

print(f"[COMPLETE] Perfectly processed and saved {len(zone_features)} zones!")
