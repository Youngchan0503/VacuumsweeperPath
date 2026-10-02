import os
import json
import csv
import math
import numpy as np
from datetime import datetime

# 1. 26개 측정소 로드
def load_stations_csv(csv_path='data/stations.csv'):
    stations = []
    if not os.path.exists(csv_path):
        return stations
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row.get('위도', 0))
                lng = float(row.get('경도', 0))
                stations.append({
                    'code': (row.get('측정소코드') or '').strip(),
                    'name': (row.get('측정소명') or '').strip(),
                    'network': (row.get('측정망') or '도시대기').strip(),
                    'lat': lat,
                    'lng': lng
                })
            except (ValueError, TypeError):
                continue
    return stations

# 2. 142개 읍·면·동 GeoJSON 로드 및 대표 중심점 계산
def load_dong_centroids(geojson_path='static/data/daegu_dong.geojson'):
    dongs = []
    if not os.path.exists(geojson_path):
        return dongs
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for feat in data.get('features', []):
        props = feat.get('properties', {})
        geom = feat.get('geometry', {})
        dist = props.get('district', '')
        dong = props.get('dong', '')
        full_name = props.get('fullName', f"대구광역시 {dist} {dong}")
        
        # 중심점 계산
        coords = geom.get('coordinates', [])
        gtype = geom.get('type', '')
        all_pts = []
        if gtype == 'Polygon':
            for ring in coords:
                all_pts.extend(ring)
        elif gtype == 'MultiPolygon':
            for poly in coords:
                for ring in poly:
                    all_pts.extend(ring)
        
        if all_pts:
            avg_lng = sum(p[0] for p in all_pts) / len(all_pts)
            avg_lat = sum(p[1] for p in all_pts) / len(all_pts)
        else:
            avg_lng, avg_lat = 128.6014, 35.8714
        
        dongs.append({
            'district': dist,
            'dong': dong,
            'fullName': full_name,
            'lat': avg_lat,
            'lng': avg_lng
        })
    return dongs

# 3. Haversine 거리 공식 (km 단위)
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # 지구 반지름 (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 4. IDW 공간 보간 알고리즘 (daegu_dust2.ipynb 규격 완벽 일치)
# - PM10: 도시대기 측정망 우선 (k=20, power=1.5)
# - PM2.5: 전체 측정망 (k=15, power=1.5)
def calculate_dong_idw_air(station_values_map, stations_info, dong_list):
    """
    station_values_map: { '수창동': {'pm10': 45, 'pm25': 23}, ... }
    """
    results = {}
    
    # 유효한 측정소 필터링
    valid_pm10_stations = []
    valid_pm25_stations = []
    
    for s in stations_info:
        name = s['name']
        v = station_values_map.get(name) or {}
        p10 = v.get('pm10')
        p25 = v.get('pm25')
        
        # PM10: 도시대기 위주
        if p10 is not None and str(p10) not in ('-', '', 'None'):
            try:
                num_p10 = float(p10)
                if s['network'] == '도시대기':
                    valid_pm10_stations.append((s['lat'], s['lng'], num_p10, name))
            except ValueError:
                pass
        
        # PM2.5: 전체 측정망
        if p25 is not None and str(p25) not in ('-', '', 'None'):
            try:
                num_p25 = float(p25)
                valid_pm25_stations.append((s['lat'], s['lng'], num_p25, name))
            except ValueError:
                pass
    
    # fallback: 도시대기만으로 부족하면 전체 측정소 사용
    if len(valid_pm10_stations) < 3:
        for s in stations_info:
            name = s['name']
            v = station_values_map.get(name) or {}
            p10 = v.get('pm10')
            if p10 is not None and str(p10) not in ('-', '', 'None'):
                try:
                    num_p10 = float(p10)
                    valid_pm10_stations.append((s['lat'], s['lng'], num_p10, name))
                except ValueError:
                    pass

    def _idw(target_lat, target_lng, train_data, power=1.5, k=20):
        if not train_data:
            return None, None
        
        # 거리 계산
        dist_list = []
        for (lat, lng, val, name) in train_data:
            d = haversine_km(target_lat, target_lng, lat, lng)
            dist_list.append((d, val, name))
        
        # 거리순 정렬
        dist_list.sort(key=lambda x: x[0])
        actual_k = min(k, len(dist_list))
        top_k = dist_list[:actual_k]
        
        # 0 거리 체크
        for (d, val, name) in top_k:
            if d < 0.05:  # 50m 이내
                return val, dist_list[0]
        
        weights = [1.0 / (d ** power) for (d, val, name) in top_k]
        sum_w = sum(weights)
        if sum_w == 0:
            return top_k[0][1], dist_list[0]
        
        pred = sum(w * v for w, (d, v, name) in zip(weights, top_k)) / sum_w
        return pred, dist_list[0]

    for d in dong_list:
        dist = d['district']
        dong = d['dong']
        key = f"{dist}_{dong}"
        
        pred_pm10, nearest_pm10 = _idw(d['lat'], d['lng'], valid_pm10_stations, power=1.5, k=20)
        pred_pm25, nearest_pm25 = _idw(d['lat'], d['lng'], valid_pm25_stations, power=1.5, k=15)
        
        # 기본 fallback
        final_pm10 = round(pred_pm10, 1) if pred_pm10 is not None else 65.0
        final_pm25 = round(pred_pm25, 1) if pred_pm25 is not None else 32.0
        
        # 4단계 통합 대기등급 산출 (PM10: 30/80/150, PM2.5: 15/35/75)
        def _get_grade(v10, v25):
            # PM10
            if v10 <= 30: g10 = 1, '좋음', '#3b82f6'
            elif v10 <= 80: g10 = 2, '보통', '#10b981'
            elif v10 <= 150: g10 = 3, '나쁨', '#f59e0b'
            else: g10 = 4, '매우나쁨', '#ef4444'
            
            # PM2.5
            if v25 <= 15: g25 = 1, '좋음', '#3b82f6'
            elif v25 <= 35: g25 = 2, '보통', '#10b981'
            elif v25 <= 75: g25 = 3, '나쁨', '#f59e0b'
            else: g25 = 4, '매우나쁨', '#ef4444'
            
            return g25 if g25[0] > g10[0] else g10
        
        lvl, txt, color = _get_grade(final_pm10, final_pm25)
        
        nearest_sttn_name = nearest_pm10[2] if nearest_pm10 else '대구측정소'
        nearest_dist_km = round(nearest_pm10[0], 2) if nearest_pm10 else 0.0
        
        results[key] = {
            'district': dist,
            'dong': dong,
            'fullName': d['fullName'],
            'lat': d['lat'],
            'lng': d['lng'],
            'pm10': final_pm10,
            'pm25': final_pm25,
            'level': lvl,
            'text': txt,
            'color': color,
            'nearest_station': nearest_sttn_name,
            'nearest_dist_km': nearest_dist_km
        }
    
    # CSV 저장 (daegu_dust2.ipynb 규격)
    save_idw_to_csv(results)
    
    return results

def save_idw_to_csv(dong_idw_results, out_dir='data/realtime_idw', out_filename='daegu_dong_realtime_idw.csv'):
    """daegu_dust2.ipynb와 동일하게 행정동별 IDW 보간 결과를 CSV로 저장"""
    try:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, out_filename)
        fieldnames = ['district', 'dong', 'fullName', 'lat', 'lng', 'PM10', 'PM2.5', 'level', 'text', 'color', 'nearest_station', 'nearest_dist_km']
        with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for k, r in dong_idw_results.items():
                writer.writerow({
                    'district': r['district'],
                    'dong': r['dong'],
                    'fullName': r['fullName'],
                    'lat': r['lat'],
                    'lng': r['lng'],
                    'PM10': r['pm10'],
                    'PM2.5': r['pm25'],
                    'level': r['level'],
                    'text': r['text'],
                    'color': r['color'],
                    'nearest_station': r['nearest_station'],
                    'nearest_dist_km': r['nearest_dist_km']
                })
        print(f"[Interpolator] {len(dong_idw_results)}개 행정동 IDW CSV 저장 완료 -> {out_path}")
    except Exception as e:
        print(f"[Interpolator] CSV 저장 실패: {e}")

_CACHED_STATIONS = None
_CACHED_DONGS = None

def get_dong_idw_air(station_crawl_results):
    """
    collector에서 크롤링한 26개 측정소 데이터를 받아 142개 읍·면·동별 IDW 대기질 산출
    """
    global _CACHED_STATIONS, _CACHED_DONGS
    if _CACHED_STATIONS is None:
        _CACHED_STATIONS = load_stations_csv()
    if _CACHED_DONGS is None:
        _CACHED_DONGS = load_dong_centroids()
    
    import re
    # station_crawl_results: { '701': {'station_name': '수창동', 'pm10': 60, 'pm25': 28}, ... }
    sttn_vals = {}
    for sttn_cd, info in station_crawl_results.items():
        st_name = info.get('station_name') or info.get('name') or ''
        clean_name = re.sub(r'\(.*?\)', '', st_name).strip()
        sttn_vals[clean_name] = {
            'pm10': info.get('pm10'),
            'pm25': info.get('pm25')
        }
    
    return calculate_dong_idw_air(sttn_vals, _CACHED_STATIONS, _CACHED_DONGS)


if __name__ == '__main__':
    stations = load_stations_csv()
    dongs = load_dong_centroids()
    print(f"Loaded {len(stations)} stations, {len(dongs)} dongs.")
    
    # Dummy values test
    dummy_vals = {s['name']: {'pm10': 70 + np.random.randint(-20, 20), 'pm25': 35 + np.random.randint(-15, 15)} for s in stations}
    res = calculate_dong_idw_air(dummy_vals, stations, dongs)
    print(f"Calculated IDW air for {len(res)} dongs successfully.")
    sample = list(res.values())[0]
    print("Sample dong result:", sample)
