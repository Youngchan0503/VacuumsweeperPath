import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup
import json
import re

def crawl_daegu_air(sttn_cd='701', date_str='2026-10-01'):
    """
    대구 실시간 대기정보 시스템 크롤링
    URL: https://air.daegu.go.kr/front/realTimeAir/realTimeTotalAirView.do
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"https://air.daegu.go.kr/front/realTimeAir/realTimeTotalAirView.do?sttn_cd={sttn_cd}&from={date_str}&fromtime=00&to={date_str}&totime=23"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    try:
        html = urllib.request.urlopen(req, context=ctx, timeout=12).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return []

    # 측정소 목록 파싱
    stations = {}
    sttn_sel = soup.find('select', {'name': 'sttn_cd'})
    if sttn_sel:
        for opt in sttn_sel.find_all('option'):
            stations[opt.get('value')] = opt.text.strip()

    # 테이블 행 파싱
    rows = table.find_all('tr')
    parsed_records = []

    for r in rows:
        tds = r.find_all('td')
        if len(tds) < 16:
            continue

        # 16개 열 구조:
        # tds[0]: 일시 (예: 2026-10-01 17:00)
        # tds[1]: CAI 주원인물질 (예: O3)
        # tds[2]: CAI 등급 아이콘 img
        # tds[3]: CAI 지수 (예: 67)
        # tds[4]: PM2.5 등급 아이콘 img
        # tds[5]: PM2.5 농도 (예: 17)
        # tds[6]: PM10 등급 아이콘 img
        # tds[7]: PM10 농도 (예: 27)
        # tds[8]: O3 등급 아이콘 img
        # tds[9]: O3 지수 (예: 67)
        # tds[10]: CO 등급 아이콘 img
        # tds[11]: CO 지수 (예: 12)
        # tds[12]: SO2 등급 아이콘 img
        # tds[13]: SO2 지수 (예: 6)
        # tds[14]: NO2 등급 아이콘 img
        # tds[15]: NO2 지수 (예: 15)

        def get_grade(td):
            img = td.find('img')
            if not img or not img.get('src'):
                return 'unknown'
            src = img['src']
            if 'lv1' in src:
                return '좋음'
            elif 'lv2' in src:
                return '보통'
            elif 'lv3' in src:
                return '나쁨'
            elif 'lv4' in src:
                return '매우나쁨'
            return '보통'

        def get_clean_text(td):
            return td.text.strip().replace('\xa0', '').replace('\n', '')

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
            'cai': {
                'substance': cai_substance,
                'grade': cai_grade,
                'value': cai_val
            },
            'pm25': {
                'grade': pm25_grade,
                'value': pm25_val
            },
            'pm10': {
                'grade': pm10_grade,
                'value': pm10_val
            },
            'o3': {
                'grade': o3_grade,
                'value': o3_val
            },
            'co': {
                'grade': co_grade,
                'value': co_val
            },
            'so2': {
                'grade': so2_grade,
                'value': so2_val
            },
            'no2': {
                'grade': no2_grade,
                'value': no2_val
            }
        })

    return {
        'sttn_cd': sttn_cd,
        'station_name': stations.get(sttn_cd, '수창동'),
        'date': date_str,
        'stations': stations,
        'records': parsed_records
    }

if __name__ == '__main__':
    result = crawl_daegu_air('701', '2026-10-01')
    print("Total parsed records:", len(result['records']))
    if result['records']:
        latest = result['records'][-1]
        print("Latest record:")
        print(json.dumps(latest, ensure_ascii=False, indent=2))
