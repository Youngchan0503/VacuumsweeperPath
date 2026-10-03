import json
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import unary_union

# 1. Load daegu_dong.geojson
with open("static/data/daegu_dong.geojson", "r", encoding="utf-8") as f:
    dong_geojson = json.load(f)

# 2. Define mountain / forest exclusion polygons for Daegu with high precision
MOUNTAIN_POLYGONS = [
    # 1. 앞산 (대덕산, 산성산, 비파산, 용두산) - 남구/수성구 남측 거대 산림 (대명/봉덕/파동 남측)
    Polygon([
        [128.552, 35.830], [128.568, 35.834], [128.588, 35.832], [128.605, 35.828],
        [128.618, 35.818], [128.612, 35.792], [128.572, 35.788], [128.545, 35.802],
        [128.542, 35.818], [128.552, 35.830]
    ]),
    
    # 2. 와룡산 (달서구 이곡/신당 북서측 & 서구 이현/상중이 서측 산림)
    Polygon([
        [128.502, 35.864], [128.516, 35.868], [128.532, 35.876], [128.539, 35.888],
        [128.528, 35.898], [128.508, 35.896], [128.492, 35.885], [128.493, 35.870],
        [128.502, 35.864]
    ]),

    # 3. 함지산 / 운암지 북측 산림 (북구 7구간 칠곡 동측 & 14구간 무태조야 서측)
    Polygon([
        [128.556, 35.922], [128.570, 35.926], [128.586, 35.938], [128.598, 35.958],
        [128.586, 35.972], [128.558, 35.968], [128.542, 35.945], [128.546, 35.928],
        [128.556, 35.922]
    ]),

    # 4. 도덕산 / 명봉산 (북구 7구간 칠곡 북서측 명봉산림)
    Polygon([
        [128.502, 35.938], [128.522, 35.946], [128.538, 35.962], [128.542, 35.986],
        [128.522, 36.012], [128.488, 35.992], [128.482, 35.958], [128.502, 35.938]
    ]),

    # 5. 팔공산 국립공원 남측 거대 산림 (동구 공산/도평/평광동 북동측 산림)
    Polygon([
        [128.625, 35.946], [128.652, 35.942], [128.688, 35.946], [128.725, 35.962],
        [128.752, 35.982], [128.772, 36.022], [128.652, 36.042], [128.588, 35.992],
        [128.602, 35.962], [128.625, 35.946]
    ]),

    # 6. 초례봉 / 환성산 (동구 혁신도시 신서/각산/안심 북동측 능선 산림)
    Polygon([
        [128.722, 35.884], [128.742, 35.896], [128.772, 35.912], [128.788, 35.942],
        [128.762, 35.962], [128.722, 35.932], [128.708, 35.902], [128.722, 35.884]
    ]),

    # 7. 용지봉 / 병풍산 / 대덕산 (수성구 범물/지산/파동 남측 & 고산/연호 남측 산림)
    Polygon([
        [128.626, 35.814], [128.652, 35.818], [128.682, 35.814], [128.712, 35.818],
        [128.732, 35.802], [128.708, 35.768], [128.648, 35.768], [128.618, 35.788],
        [128.626, 35.814]
    ]),

    # 8. 삼필봉 / 청룡산 (달서구 월배/도원/진천 남측 수목원 배후 산림)
    Polygon([
        [128.512, 35.796], [128.536, 35.800], [128.552, 35.792], [128.562, 35.772],
        [128.536, 35.752], [128.502, 35.768], [128.512, 35.796]
    ]),

    # 9. 비슬산 / 최정산 (달성군 유가/구지/현풍/논공 동측 거대 산림)
    Polygon([
        [128.482, 35.658], [128.512, 35.678], [128.542, 35.708], [128.562, 35.748],
        [128.602, 35.738], [128.582, 35.658], [128.538, 35.628], [128.482, 35.658]
    ]),

    # 10. 대니산 (달성군 구지/현풍 서측 산지)
    Polygon([
        [128.402, 35.652], [128.428, 35.658], [128.438, 35.678], [128.428, 35.698],
        [128.402, 35.692], [128.392, 35.668], [128.402, 35.652]
    ]),

    # 11. 마천산 / 궁산 / 하빈 배후 산림 (달성군 6구간 다사/하빈/화원 배후 산지)
    Polygon([
        [128.418, 35.868], [128.448, 35.882], [128.458, 35.918], [128.432, 35.942],
        [128.392, 35.922], [128.398, 35.878], [128.418, 35.868]
    ])
]

mountains_union = unary_union(MOUNTAIN_POLYGONS)

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
        print(f"Zone {zone_id}: No polygons found")
        continue
        
    # Dissolve all dong polygons belonging to this zone
    zone_full_geom = unary_union(polys)
    
    # Subtract mountain exclusion areas (산림/임야 제외)
    urban_geom = zone_full_geom.difference(mountains_union)
    
    if urban_geom.is_empty:
        urban_geom = zone_full_geom
        
    # Simplify slightly for smooth and ultra-fast web rendering
    urban_geom_simplified = urban_geom.simplify(0.0001, preserve_topology=True)
    
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
    print(f"Zone {zone_id} ({z['name']}): Generated urban polygon without mountain wilderness ({urban_geom_simplified.geom_type})")

output_geojson = {
    "type": "FeatureCollection",
    "features": zone_features
}

output_path = "static/data/daegu_15_urban_zones.geojson"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output_geojson, f, ensure_ascii=False)

print(f"\n[COMPLETE] Successfully written {len(zone_features)} mountain-excluded urban zones to {output_path}!")
