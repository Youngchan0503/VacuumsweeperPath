import json
import sys
from shapely.geometry import shape, mapping, Polygon, MultiPolygon, Point
from shapely.ops import unary_union

sys.stdout.reconfigure(encoding='utf-8')

# 1. Load dong geojson
with open("static/data/daegu_dong.geojson", "r", encoding="utf-8") as f:
    dong_geojson = json.load(f)

# 2. Mountain & Forest Exclusion Masks
MOUNTAIN_PEAKS = [
    # 앞산 / 대덕산 정상부 (남구/수성구 남측 암벽·산림)
    Polygon([
        [128.560, 35.825], [128.575, 35.828], [128.605, 35.820], [128.615, 35.805],
        [128.610, 35.792], [128.575, 35.788], [128.550, 35.805], [128.560, 35.825]
    ]),

    # 비슬산 주능선 (유가/현풍 동측 능선 - 테크노 도심 128.46~128.48 보존)
    Polygon([
        [128.482, 35.620], [128.485, 35.655], [128.480, 35.685], [128.482, 35.710],
        [128.488, 35.730], [128.520, 35.740], [128.580, 35.730], [128.580, 35.620],
        [128.482, 35.620]
    ]),

    # 금계산 중앙 산림 (옥포 도심과 논공 달성산단 사이 산지)
    Polygon([
        [128.458, 35.760], [128.472, 35.765], [128.478, 35.775], [128.472, 35.785],
        [128.458, 35.782], [128.452, 35.770], [128.458, 35.760]
    ]),

    # 대니산 산림 (구지 자모리/오설리 및 현풍 서측 산지 - 국가산단 보존)
    Polygon([
        [128.390, 35.680], [128.418, 35.685], [128.438, 35.700], [128.435, 35.720],
        [128.405, 35.715], [128.380, 35.695], [128.390, 35.680]
    ]),

    # 옥포 송해공원 동측 산지 (대곡2지구 한실로/갈밭로 침범하지 않음)
    Polygon([
        [128.500, 35.760], [128.518, 35.765], [128.520, 35.782], [128.508, 35.788],
        [128.495, 35.780], [128.500, 35.760]
    ]),

    # 팔공산 국립공원 고지대 능선
    Polygon([
        [128.630, 35.960], [128.680, 35.960], [128.730, 35.975], [128.765, 36.015],
        [128.650, 36.035], [128.595, 35.985], [128.630, 35.960]
    ]),

    # 와룡산 정상부
    Polygon([
        [128.505, 35.872], [128.520, 35.876], [128.532, 35.885], [128.525, 35.895],
        [128.505, 35.892], [128.498, 35.880], [128.505, 35.872]
    ]),

    # 초례봉 / 환성산 능선
    Polygon([
        [128.730, 35.890], [128.750, 35.900], [128.775, 35.920], [128.785, 35.942],
        [128.760, 35.960], [128.725, 35.930], [128.715, 35.905], [128.730, 35.890]
    ]),

    # 용지봉 / 병풍산 고지대
    Polygon([
        [128.635, 35.812], [128.660, 35.816], [128.690, 35.812], [128.720, 35.816],
        [128.730, 35.800], [128.705, 35.768], [128.648, 35.768], [128.625, 35.788],
        [128.635, 35.812]
    ]),

    # 청룡산 / 삼필봉 남측 고지대 (대곡2지구 한실로/갈밭로는 보존)
    Polygon([
        [128.500, 35.740], [128.505, 35.792], [128.520, 35.795], [128.540, 35.792],
        [128.558, 35.790], [128.585, 35.795], [128.588, 35.740], [128.540, 35.730],
        [128.500, 35.740]
    ]),

    # 마천산 배후 산림
    Polygon([
        [128.415, 35.875], [128.442, 35.890], [128.450, 35.925], [128.425, 35.942],
        [128.390, 35.920], [128.395, 35.880], [128.415, 35.875]
    ])
]

mountains_union = unary_union(MOUNTAIN_PEAKS)

# 12 Optimal Balanced Zones (전 구간 200~250km 균형 배차 & 1:1 차량 전담 최적화)
zones_def = [
  {
    'id': 1,
    'name': '1구간 (성서산단·이곡·용산)',
    'matchDistricts': ['달서구'],
    'matchKeywords': ['신당', '이곡', '호림', '갈산', '파호', '대천', '월암', '용산', '장기', '장동']
  },
  {
    'id': 2,
    'name': '2구간 (서대구산단·평리·비산·내당)',
    'matchDistricts': ['서구'],
    'matchKeywords': ['이현', '평리', '비산', '원대', '상중이', '내당']
  },
  {
    'id': 3,
    'name': '3구간 (칠곡지구·태전·구암·관음·국우·도남)',
    'matchDistricts': ['북구'],
    'matchKeywords': ['태전', '구암', '관음', '읍내', '동천', '국우', '학정', '관문']
  },
  {
    'id': 4,
    'name': '4구간 (검단·유통단지·산격·서변·동변·연경)',
    'matchDistricts': ['북구'],
    'matchKeywords': ['산격', '복현', '검단', '서변', '동변', '연경', '무태조야']
  },
  {
    'id': 5,
    'name': '5구간 (중구 원도심·침산·노원 3공단·칠성)',
    'matchDistricts': ['중구', '북구'],
    'matchKeywords': ['동인', '삼덕', '성내', '대신', '남산', '대봉', '칠성', '침산', '고성', '노원', '대현']
  },
  {
    'id': 6,
    'name': '6구간 (동대구도심·신천·신암·효목·공항·불로)',
    'matchDistricts': ['동구'],
    'matchKeywords': ['신천', '신암', '효목', '불로', '봉무', '지저', '공산']
  },
  {
    'id': 7,
    'name': '7구간 (신서혁신·안심·율하·동촌·방촌)',
    'matchDistricts': ['동구'],
    'matchKeywords': ['율하', '동호', '신서', '서호', '각산', '안심', '혁신', '동촌', '방촌', '해안', '도평']
  },
  {
    'id': 8,
    'name': '8구간 (수성도심·범어·만촌·시지·알파시티)',
    'matchDistricts': ['수성구'],
    'matchKeywords': ['범어', '만촌', '수성', '고산', '시지', '신매', '사월', '매호', '가천', '삼덕', '연호', '이천', '노변', '대흥']
  },
  {
    'id': 9,
    'name': '9구간 (남구전역·대명·봉덕·지산·범물·두산)',
    'matchDistricts': ['남구', '수성구'],
    'matchKeywords': ['대명', '봉덕', '이천', '지산', '범물', '황금', '두산', '상동', '중동', '파동']
  },
  {
    'id': 10,
    'name': '10구간 (월배·상인·도원·대곡·진천·두류)',
    'matchDistricts': ['달서구'],
    'matchKeywords': ['월성', '진천', '상인', '유천', '대곡', '도원', '본리', '본동', '송현', '감삼', '두류', '성당', '죽전']
  },
  {
    'id': 11,
    'name': '11구간 (달성중북부·다사·하빈·화원·논공·옥포)',
    'matchDistricts': ['달성군'],
    'matchKeywords': ['다사', '하빈', '화원', '논공', '옥포']
  },
  {
    'id': 12,
    'name': '12구간 (달성남부·테크노·대구국가산단·구지·현풍)',
    'matchDistricts': ['달성군'],
    'matchKeywords': ['유가', '구지', '현풍']
  }
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
        print(f"Warning: Zone {zone_id} has no polygons!")
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
    print(f"Processed Zone {zone_id:02d} ({z['name']}) -> {urban_geom_simplified.geom_type}")

output_geojson = {
    "type": "FeatureCollection",
    "features": zone_features
}

output_path = "static/data/daegu_15_urban_zones.geojson"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output_geojson, f, ensure_ascii=False)

print(f"\n[COMPLETE] Successfully generated {len(zone_features)} optimal balanced zones (1~12구간) to {output_path}!")
