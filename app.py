import os
from flask import Flask, render_template, jsonify, request
import config
import collector
import analyzer

app = Flask(__name__)
app.secret_key = 'daegu-dust-vehicle-analysis-2026'

@app.route('/')
def index():
    """지도 중심의 대구 분진흡입차량 운행 경로 개선도 분석 메인 뷰"""
    analysis = analyzer.analyze_dust_routes()
    return render_template(
        'index.html',
        kpis=analysis['kpis'],
        districts=config.DAEGU_DISTRICTS,
        map_center=config.DAEGU_MAP_CENTER
    )

@app.route('/api/analysis', methods=['GET'])
def api_analysis():
    """대구 분진흡입차량 경로 및 개선도 분석 데이터 API"""
    data = analyzer.analyze_dust_routes()
    return jsonify({'success': True, 'data': data})

@app.route('/api/routes', methods=['GET'])
def api_routes():
    """대구 도로 노선 및 Before/After 경로 데이터 API"""
    routes = collector.get_routes()
    return jsonify({'success': True, 'routes': routes})

@app.route('/api/vehicles', methods=['GET'])
def api_vehicles():
    """대구 분진흡입차량 목록 및 운행 데이터 API"""
    vehicles = collector.get_vehicles()
    return jsonify({'success': True, 'vehicles': vehicles})

@app.route('/api/air/realtime', methods=['GET'])
def api_air_realtime():
    """대구광역시 실시간 대기정보 크롤링 API (air.daegu.go.kr)"""
    sttn_cd = request.args.get('sttn_cd', '701')
    date_str = request.args.get('date', '2026-10-01')
    data = collector.crawl_daegu_realtime_air(sttn_cd=sttn_cd, date_str=date_str)
    return jsonify({'success': True, 'data': data})

@app.route('/api/air/districts', methods=['GET'])
def api_air_districts():
    """8개 자치구별 미세먼지(PM10) 등급 및 색상 데이터 API"""
    data = collector.get_all_districts_air_summary()
    return jsonify({'success': True, 'districts': data})

@app.route('/api/daegu/dong-geojson', methods=['GET'])
def api_dong_geojson():
    """대구 142개 읍·면·동 행정구역 GeoJSON API"""
    import json
    path = os.path.join(app.root_path, 'static', 'data', 'daegu_dong.geojson')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({'type': 'FeatureCollection', 'features': []})

if __name__ == '__main__':
    print("==================================================")
    print(" Daegu Dust Vehicle Route Improvement Analysis")
    print(" URL: http://127.0.0.1:5050")
    print("==================================================")
    app.run(debug=True, host='0.0.0.0', port=5050)
