import os
import json
import ssl
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import config

# ==========================================================================
# 파일 기반 시간별 캐시 (서버 재시작 후에도 유지, 정각 단위로 캐시 공유)
# 캐시 키 형식: {sttn_cd}_{YYYY-MM-DD}_{HH}  (14:10이든 14:59이든 '14' 동일)
# ==========================================================================
_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data', 'air_cache')
os.makedirs(_CACHE_DIR, exist_ok=True)

# 메모리 캐시 (파일 읽기 횟수 최소화용 2차 캐시)
_MEM_CACHE = {}

def _get_hour_cache_key(sttn_cd: str, date_str: str) -> str:
    """현재 시각 기준 시간 단위 캐시 키 생성 (예: 701_2026-10-02_14)"""
    now_hour = datetime.now().strftime('%H')
    return f"{sttn_cd}_{date_str}_{now_hour}"

def _cache_file_path(cache_key: str) -> str:
    return os.path.join(_CACHE_DIR, f"{cache_key}.json")

def _load_cache(cache_key: str):
    """파일 캐시 → 메모리 캐시 순서로 조회. 없으면 None 반환."""
    if cache_key in _MEM_CACHE:
        return _MEM_CACHE[cache_key]
    fpath = _cache_file_path(cache_key)
    if os.path.exists(fpath):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _MEM_CACHE[cache_key] = data
            return data
        except Exception as e:
            print(f"[AirCache] 캐시 파일 읽기 실패 ({fpath}): {e}")
    return None

def _save_cache(cache_key: str, data: dict):
    """메모리 + 파일 양쪽에 캐시 저장."""
    _MEM_CACHE[cache_key] = data
    fpath = _cache_file_path(cache_key)
    try:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AirCache] 캐시 파일 저장 실패 ({fpath}): {e}")

def _cleanup_old_cache(keep_days: int = 2):
    """오래된 캐시 파일 정리 (기본 2일 이상 지난 파일 삭제)"""
    now = datetime.now()
    try:
        for fname in os.listdir(_CACHE_DIR):
            fpath = os.path.join(_CACHE_DIR, fname)
            if not fname.endswith('.json'):
                continue
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if (now - mtime).days >= keep_days:
                os.remove(fpath)
    except Exception as e:
        print(f"[AirCache] 캐시 정리 실패: {e}")

# 자치구별 대표 대기측정소 매핑
DISTRICT_STATION_MAP = {
    '중구': {'sttn_cd': '701', 'name': '수창동'},
    '남구': {'sttn_cd': '702', 'name': '대명동'},
    '수성구': {'sttn_cd': '703', 'name': '만촌동'},
    '동구': {'sttn_cd': '704', 'name': '신암동'},
    '북구': {'sttn_cd': '705', 'name': '노원동'},
    '서구': {'sttn_cd': '709', 'name': '이현동'},
    '달서구': {'sttn_cd': '710', 'name': '호산동'},
    '달성군': {'sttn_cd': '714', 'name': '다사읍'}
}

# 대구 주요 측정소 전체 이름 사전
STATION_NAMES = {
    '701': '수창동(중구)',
    '702': '대명동(남구)',
    '703': '만촌동(수성구)',
    '704': '신암동(동구)',
    '705': '노원동(북구)',
    '707': '지산동(수성구)',
    '708': '태전동(북구)',
    '709': '이현동(서구)',
    '710': '호산동(달서구)',
    '711': '현풍읍(달성군)',
    '712': '시지동(수성구)',
    '713': '율하동(동구)',
    '714': '다사읍(달성군)',
    '715': '서호동(동구)',
    '716': '본동(달서구)',
    '717': '화원읍(달성군)',
    '718': '진천동(달서구)',
    '719': '침산동(북구)',
    '720': '대명11동(남구)',
    '721': '봉무동(동구)',
    '802': '평리동(서구)',
    '803': '이곡동(달서구)'
}

def load_daegu_data():
    """대구 분진흡입차량 운행 경로 및 환경 데이터셋 로드"""
    path = config.DAEGU_ROUTES_JSON_PATH
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_routes():
    """대구 주요 도로 및 경로 목록 반환"""
    data = load_daegu_data()
    return data.get('routes', [])

def get_vehicles():
    """대구 분진흡입차량 목록 및 운행 스탯 반환"""
    data = load_daegu_data()
    return data.get('vehicles', [])

def get_monitoring_stations():
    """대구 대기질/미세먼지 측정소 목록 반환"""
    data = load_daegu_data()
    return data.get('monitoring_stations', [])

def crawl_daegu_realtime_air(sttn_cd='701', date_str=None):
    """
    대구광역시 실시간 대기정보 시스템 크롤링
    대상 URL: https://air.daegu.go.kr/front/realTimeAir/realTimeTotalAirView.do
    - date_str 미지정 시 현재 날짜(오늘) 자동 적용
    - 캐시 키: {sttn_cd}_{date}_{hour} → 같은 시간대 재접속 시 파일 캐시 즉시 반환
    - 과거 날짜 조회는 시간 단위 캐시 키 없이 날짜+시간 고정 캐시 사용
    """
    today_str = datetime.now().strftime('%Y-%m-%d')
    is_today = (not date_str) or (date_str == today_str)
    if not date_str:
        date_str = today_str

    # 오늘 데이터: 시간 단위 캐시 키 (14:10 = 14:59 동일 키)
    # 과거 데이터: 날짜 고정 캐시 키 (변하지 않으므로 시간 무관)
    if is_today:
        cache_key = _get_hour_cache_key(sttn_cd, date_str)
    else:
        cache_key = f"{sttn_cd}_{date_str}_all"

    # 파일/메모리 캐시 확인 → 있으면 즉시 반환 (크롤링 없음)
    cached = _load_cache(cache_key)
    if cached:
        print(f"[AirCache] 캐시 HIT: {cache_key}")
        return cached

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"https://air.daegu.go.kr/front/realTimeAir/realTimeTotalAirView.do?sttn_cd={sttn_cd}&from={date_str}&fromtime=00&to={date_str}&totime=23"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    try:
        html = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[AirCrawler] 크롤링 오류 ({url}): {e}")
        # 오류 시 캐시가 있으면 캐시 반환, 없으면 빈 구조
        if cache_key in _AIR_CACHE:
            return _AIR_CACHE[cache_key]
        return {
            'sttn_cd': sttn_cd,
            'station_name': STATION_NAMES.get(sttn_cd, '대구측정소'),
            'date': date_str,
            'records': [],
            'latest': None
        }

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return {
            'sttn_cd': sttn_cd,
            'station_name': STATION_NAMES.get(sttn_cd, '대구측정소'),
            'date': date_str,
            'records': [],
            'latest': None
        }

    def get_grade(td):
        img = td.find('img')
        if not img or not img.get('src'):
            return {'level': 1, 'text': '좋음', 'class': 'grade-good', 'icon': 'smile'}
        src = img['src']
        if 'lv1' in src:
            return {'level': 1, 'text': '좋음', 'class': 'grade-good', 'icon': 'smile'}
        elif 'lv2' in src:
            return {'level': 2, 'text': '보통', 'class': 'grade-moderate', 'icon': 'smile'}
        elif 'lv3' in src:
            return {'level': 3, 'text': '나쁨', 'class': 'grade-bad', 'icon': 'frown'}
        elif 'lv4' in src:
            return {'level': 4, 'text': '매우나쁨', 'class': 'grade-very-bad', 'icon': 'alert-circle'}
        return {'level': 2, 'text': '보통', 'class': 'grade-moderate', 'icon': 'smile'}

    def get_clean_text(td):
        return td.text.strip().replace('\xa0', '').replace('\n', '')

    rows = table.find_all('tr')
    parsed_records = []

    for r in rows:
        tds = r.find_all('td')
        if len(tds) < 16:
            continue

        time_str = get_clean_text(tds[0])
        cai_substance = get_clean_text(tds[1])
        cai_grade = get_grade(tds[2])
        cai_val = get_clean_text(tds[3])

        pm25_grade = get_grade(tds[4])
        pm25_val = get_clean_text(tds[5])

        pm10_grade = get_grade(tds[6])
        pm10_val = get_clean_text(tds[7])

        o3_grade = get_grade(tds[8])
        o3_val = get_clean_text(tds[9])

        co_grade = get_grade(tds[10])
        co_val = get_clean_text(tds[11])

        so2_grade = get_grade(tds[12])
        so2_val = get_clean_text(tds[13])

        no2_grade = get_grade(tds[14])
        no2_val = get_clean_text(tds[15])

        parsed_records.append({
            'time': time_str,
            'cai': {'substance': cai_substance, 'grade': cai_grade, 'value': cai_val},
            'pm25': {'grade': pm25_grade, 'value': pm25_val},
            'pm10': {'grade': pm10_grade, 'value': pm10_val},
            'o3': {'grade': o3_grade, 'value': o3_val},
            'co': {'grade': co_grade, 'value': co_val},
            'so2': {'grade': so2_grade, 'value': so2_val},
            'no2': {'grade': no2_grade, 'value': no2_val}
        })

    # 당일 새벽(00~01시) 등으로 아직 관측 데이터가 올라오지 않은 경우 전일(어제) 최종 데이터로 안전 폴백
    if not parsed_records and date_str == today_str:
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"[AirCrawler] 당일({today_str}) 데이터 준비 중: 전일({yesterday_str}) 데이터 폴백 호출")
        fallback_data = crawl_daegu_realtime_air(sttn_cd=sttn_cd, date_str=yesterday_str)
        if fallback_data.get('records'):
            fallback_data['date'] = today_str
            fallback_data['is_fallback'] = True
            return fallback_data

    latest_rec = parsed_records[-1] if parsed_records else None

    result = {
        'sttn_cd': sttn_cd,
        'station_name': STATION_NAMES.get(sttn_cd, '수창동(중구)'),
        'date': date_str,
        'stations': STATION_NAMES,
        'district_map': DISTRICT_STATION_MAP,
        'records': parsed_records,
        'latest': latest_rec
    }

    # 파일 + 메모리 양쪽에 캐시 저장 (서버 재시작 후에도 즉시 사용 가능)
    _save_cache(cache_key, result)
    # 오래된 캐시 파일 정리 (2일 이상)
    _cleanup_old_cache(keep_days=2)
    return result

def get_all_districts_air_summary():
    """8개 자치구 대표 측정소 미세먼지(PM10) 및 등급 종합 반환 (실시간 크롤링 우선)"""
    data = load_daegu_data()
    stations_data = {s['district']: s['pm10'] for s in data.get('monitoring_stations', [])}
    
    results = {}
    for dist, sttn_info in DISTRICT_STATION_MAP.items():
        sttn_cd = sttn_info['sttn_cd']
        sttn_name = sttn_info['name']
        base_pm10 = stations_data.get(dist, 65)

        # crawl_daegu_realtime_air 내부에서 파일 캐시 → 메모리 캐시 → 실시간 크롤링 순서로 처리
        # 서버 재시작 후에도 파일 캐시가 있으면 즉시 반환되므로 별도 캐시 탐색 불필요
        try:
            realtime = crawl_daegu_realtime_air(sttn_cd=sttn_cd)
            latest = realtime.get('latest')
            if latest and latest.get('pm10') and latest['pm10'].get('value'):
                val = int(latest['pm10']['value'])
            else:
                val = base_pm10
        except Exception as e:
            print(f"[AirSummary] {dist}({sttn_cd}) 크롤링 실패 → 기본값 사용: {e}")
            val = base_pm10
            
        # PM10 등급 판정 (AirKorea 기준: 좋음 0~30, 보통 31~80, 나쁨 81~150, 매우나쁨 151~)
        if val <= 30:
            level = 1
            text = '좋음'
            color = '#3b82f6'
        elif val <= 80:
            level = 2
            text = '보통'
            color = '#10b981'
        elif val <= 150:
            level = 3
            text = '나쁨'
            color = '#f59e0b'
        else:
            level = 4
            text = '매우나쁨'
            color = '#ef4444'
            
        results[dist] = {
            'district': dist,
            'sttn_cd': sttn_cd,
            'sttn_name': sttn_name,
            'pm10': val,
            'level': level,
            'text': text,
            'color': color
        }
    return results

