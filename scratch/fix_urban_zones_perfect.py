import json
import sys
from shapely.geometry import shape, mapping, Polygon, MultiPolygon, Point
from shapely.ops import unary_union

sys.stdout.reconfigure(encoding='utf-8')

# 1. Load dong geojson
with open("static/data/daegu_dong.geojson", "r", encoding="utf-8") as f:
    dong_geojson = json.load(f)

# 2. Mountain & Forest Exclusion Masks for Daegu (Precise uninhabited nature reserve peaks & mountain slopes)
MOUNTAIN_PEAKS = [
    # 1. 앞산 / 대덕산 / 산성산 고지대 능선 (남구 봉덕/대명 및 수성구 파동 남측 암벽·산림)
    Polygon([
        [128.560, 35.825], [128.575, 35.828], [128.605, 35.820], [128.615, 35.805],
        [128.610, 35.792], [128.575, 35.788], [128.550, 35.805], [128.560, 35.825]
    ]),

    # 2. [13구간 동측] 비슬산·최정산 거대 산악지대 (유가/현풍/논공/옥포 동측의 광활한 산림/계곡)
    # DGIST(128.468), 테크노폴리스(128.46~128.48), 현풍도심(128.44~128.46)은 보존하고 동측 산림만 차감
    Polygon([
        [128.482, 35.620], [128.485, 35.655], [128.480, 35.685], [128.482, 35.710],
        [128.488, 35.735], [128.498, 35.760], [128.515, 35.780], [128.550, 35.790],
        [128.600, 35.750], [128.580, 35.620], [128.482, 35.620]
    ]),

    # 3. [13구간 중앙] 금계산 / 노이리·상리·하리 중앙 산림 (옥포 도심과 논공 달성산단 사이 산지)
    Polygon([
        [128.458, 35.760], [128.472, 35.765], [128.478, 35.775], [128.472, 35.785],
        [128.458, 35.782], [128.452, 35.770], [128.458, 35.760]
    ]),

    # 4. [13구간 서측] 대니산 산림 (구지면 자모리/오설리/오산리 및 현풍 서측 산지)
    # 국가산단(128.40~128.43, 35.64~35.67) 및 구지면사무소/창리 보존
    Polygon([
        [128.390, 35.680], [128.418, 35.685], [128.438, 35.700], [128.435, 35.720],
        [128.405, 35.715], [128.380, 35.695], [128.390, 35.680]
    ]),

    # 5. [13구간 북동측] 옥포 반송리/김흥리/기세리 동측 깊은 산림 (송해공원 동측 산악지대)
    Polygon([
        [128.510, 35.775], [128.530, 35.775], [128.560, 35.800], [128.530, 35.815],
        [128.512, 35.800], [128.510, 35.775]
    ]),

    # 6. 팔공산 국립공원 남측 고지대 능선 (동구 공산/도평 북측 산림)
    Polygon([
        [128.630, 35.960], [128.680, 35.960], [128.730, 35.975], [128.765, 36.015],
        [128.650, 36.035], [128.595, 35.985], [128.630, 35.960]
    ]),

    # 7. 와룡산 정상부 (달서구 신당/이곡 북서측 & 서구 상중이 서측 산림)
    Polygon([
        [128.505, 35.872], [128.520, 35.876], [128.532, 35.885], [128.525, 35.895],
        [128.505, 35.892], [128.498, 35.880], [128.505, 35.872]
    ]),

    # 8. 초례봉 / 환성산 능선 (동구 혁신도시 신서/각산 북동측 산림)
    Polygon([
        [128.730, 35.890], [128.750, 35.900], [128.775, 35.920], [128.785, 35.942],
        [128.760, 35.960], [128.725, 35.930], [128.715, 35.905], [128.730, 35.890]
    ]),

    # 9. 용지봉 / 병풍산 고지대 (수성구 범물/지산 남측 산림)
    Polygon([
        [128.635, 35.812], [128.660, 35.816], [128.690, 35.812], [128.720, 35.816],
        [128.730, 35.800], [128.705, 35.768], [128.648, 35.768], [128.625, 35.788],
        [128.635, 35.812]
    ]),

    # 10. 청룡산 / 삼필봉 능선 (달서구 월배/도원/진천 남측 산림)
    Polygon([
        [128.515, 35.792], [128.538, 35.796], [128.552, 35.790], [128.560, 35.770],
        [128.535, 35.750], [128.505, 35.765], [128.515, 35.792]
    ]),

    # 11. 마천산 배후 산림 (달성군 다사/하빈 서북측 산림)
    Polygon([
        [128.415, 35.875], [128.442, 35.890], [128.450, 35.925], [128.425, 35.942],
        [128.390, 35.920], [128.395, 35.880], [128.415, 35.875]
    ])
]

mountains_union = unary_union(MOUNTAIN_PEAKS)

zones_def = [
  {'id': 1, 'name': '1구간 (성서산단·이곡)', 'matchDistricts': ['달서구'], 'matchKeywords': ['신당', '이곡', '호림', '갈산', '파호', '대천', '월암', '용산', '장기', '장동']},
  {'id': 2, 'name': '2구간 (서대구산단·평리·비산·내당)', 'matchDistricts': ['서구'], 'matchKeywords': ['이현', '평리', '비산', '원대', '상중이', '내당']},
  {'id': 3, 'name': '3구간 (검단·공항·유통단지·산격)', 'matchDistricts': ['북구', '동구'], 'matchKeywords': ['산격', '복현', '검단', '불로', '봉무', '지저', '공산']},
  {'id': 4, 'name': '4구간 (수성남부·지산·범물·두산·파동)', 'matchDistricts': ['수성구'], 'matchKeywords': ['지산', '범물', '황금', '두산', '상동', '중동', '파동']},
  {'id': 5, 'name': '5구간 (동대구도심·신천·신암·효목)', 'matchDistricts': ['동구'], 'matchKeywords': ['신천', '신암', '효목']},
  {'id': 6, 'name': '6구간 (다사·하빈·화원)', 'matchDistricts': ['달성군'], 'matchKeywords': ['다사', '하빈', '화원']},
  {'id': 7, 'name': '7구간 (칠곡지구·태전·구암·관음·국우·학정·도남)', 'matchDistricts': ['북구'], 'matchKeywords': ['태전', '구암', '관음', '읍내', '동천', '국우', '학정', '관문']},
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
    
    # Subtract mountain exclusion masks
    urban_geom = zone_full_geom.difference(mountains_union)
    
    if urban_geom.is_empty:
        urban_geom = zone_full_geom
        
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

print(f"[COMPLETE] Perfectly processed and saved {len(zone_features)} zones with Zone 13 mountain exclusion!")
