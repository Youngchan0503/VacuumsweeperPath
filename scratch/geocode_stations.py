import json
import urllib.request
import urllib.parse
import ssl
import re
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open('data/stations_info.json', 'r', encoding='utf-8') as f:
    raw_list = json.load(f)

stations = [x for x in raw_list if x.get('name') != '측정소명' and x.get('address') != '주소']

# 측정소별 sttn_cd 매핑
NAME_TO_CODE = {
    '수창동': '701', '지산동': '702', '서호동': '703', '이현동': '704',
    '대명동': '705', '신암동': '707', '태전동': '708', '만촌동': '709',
    '호림동': '710', '유가읍': '711', '시지동': '712', '진천동': '713',
    '다사읍': '714', '본동': '715',   '산격동': '716', '화원읍': '717',
    '내당동': '718', '침산동': '719', '남산1동': '720', '군위읍': '721',
    '평리동': '802', '이곡동': '803', '충혼탑': '804', '서변동': '805',
    '연호동': '806', '용계동': '807'
}

def geocode_vworld(query):
    # Try Nominatim OSM
    url = f'https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'DaeguDustAirTracker/1.0'})
        res = urllib.request.urlopen(req, context=ctx, timeout=5)
        data = json.loads(res.read().decode('utf-8'))
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    return None, None

results = []
for s in stations:
    name = s['name']
    s['sttn_cd'] = NAME_TO_CODE.get(name, '')
    addr = s['address']
    clean_addr = re.sub(r'\(.*?\)', '', addr).strip()
    
    # 1. 시도: 대구 + 도로명
    lat, lng = geocode_vworld(f"대구광역시 {clean_addr}")
    if not lat:
        # 2. 시도: 괄호 안 건물명 (예: 반야월초등학교, 신암5동 행정복지센터)
        match = re.search(r'\((.*?)\)', addr)
        if match:
            place = match.group(1).split()[0]
            lat, lng = geocode_vworld(f"대구 {place}")
    if not lat:
        # 3. 시도: 동 이름
        lat, lng = geocode_vworld(f"대구 {s['district']} {name}")
    
    print(f"[{s['sttn_cd']}] {s['district']} {name} -> lat: {lat}, lng: {lng} ({addr})")
    s['lat'] = lat
    s['lng'] = lng
    results.append(s)
    time.sleep(1)

with open('data/stations_geocoded.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Saved data/stations_geocoded.json successfully.")
