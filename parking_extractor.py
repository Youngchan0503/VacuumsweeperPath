"""
=============================================================================
서울시 공영주차장 실시간 누적 데이터 추출 및 분석 모듈 (Parking Data Extractor)
=============================================================================
데이터 소스: TalkFile_서울시_공영주차장_실시간_누적.numbers (1).csv

주요 기능:
1. 데이터 로드 및 전처리 (결측치 정제, 자치구 추출, 혼잡도 등급 분류)
2. 최신 실시간 주차장 현황 추출 (122개소)
3. 서울시 자치구(23개 구)별 통계 집계 (총면수, 주차대수, 잔여석, 평균 이용률)
4. 시간대별(10:39 ~ 14:39) 시계열 이용률 추이 추출
5. 만차/혼잡 상위(Top N) 및 잔여석 여유 상위(Top N) 주차장 선별
6. 주차장 유형(노외/노상) 및 과금(유료/무료)별 통계
7. 조건별 맞춤 필터링 검색 (키워드, 자치구, 최소 잔여석, 최대 이용률 등)
8. 특정 주차장의 시계열 누적 이력 추출
9. 추출 결과 CSV / JSON 내보내기
10. 독립 실행형 CLI (명령줄 인터페이스) 지원
=============================================================================
"""

import os
import sys
import argparse
import json
import pandas as pd
import numpy as np

# Windows 터미널 한글 및 유니코드 출력 안정화
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# 기본 데이터 파일 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, 'data', 'TalkFile_서울시_공영주차장_실시간_누적.numbers (1).csv')

# 전역 캐시
_CACHED_DF = None


def load_data(csv_path=None, force_reload=False):
    """
    서울시 공영주차장 실시간 누적 CSV 파일을 로드하고 전처리합니다.

    Args:
        csv_path (str, optional): CSV 파일 경로. 기본값은 data 폴더 내 파일.
        force_reload (bool): 캐시를 무시하고 새로 읽을지 여부.

    Returns:
        pd.DataFrame: 전처리가 완료된 주차장 데이터프레임
    """
    global _CACHED_DF

    if _CACHED_DF is not None and not force_reload:
        return _CACHED_DF.copy()

    path = csv_path or DEFAULT_CSV_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"주차장 데이터 파일을 찾을 수 없습니다: {path}")

    # 인코딩 대응 (utf-8 / utf-8-sig / cp949)
    try:
        df = pd.read_csv(path, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding='cp949')

    # 컬럼 공백 제거
    df.columns = [col.strip() for col in df.columns]

    # 결측치 정제 및 수치형 변환
    df['TPKCT'] = pd.to_numeric(df['TPKCT'], errors='coerce').fillna(0).astype(int)
    df['NOW_PRK_VHCL_CNT'] = pd.to_numeric(df['NOW_PRK_VHCL_CNT'], errors='coerce').fillna(0).astype(int)
    df['남은자리'] = pd.to_numeric(df['남은자리'], errors='coerce').fillna(0).astype(int)
    df['주차이용률'] = pd.to_numeric(df['주차이용률'], errors='coerce').fillna(0.0).round(2)

    # 잔여면수가 음수인 경우 보정 (오버플로우 주차 대비)
    df['남은자리'] = df['남은자리'].clip(lower=0)

    # 1. 자치구 추출 (ADDR 예: '종로구 세종로 80-1' -> '종로구')
    df['구'] = df['ADDR'].str.extract(r'([가-힣]+구)')
    df['구'] = df['구'].fillna('기타구')

    # 2. 혼잡도 상태 등급 분류
    # 90% 이상: 만차 임박 (혼잡), 70% 이상: 혼잡, 40% 이상: 보통, 40% 미만: 여유
    conditions = [
        (df['주차이용률'] >= 90.0),
        (df['주차이용률'] >= 70.0),
        (df['주차이용률'] >= 40.0)
    ]
    choices = ['만차', '혼잡', '보통']
    df['혼잡도_등급'] = np.select(conditions, choices, default='여유')

    # 3. 수집시간 문자열 정규화
    df['수집시간'] = df['수집시간'].astype(str)

    _CACHED_DF = df
    return df.copy()


def get_latest_status(df=None, district=None, parking_type=None, pay_yn=None):
    """
    최신 수집 시점(가장 최근 시간) 기준 주차장 현황을 추출합니다.

    Args:
        df (pd.DataFrame, optional): 데이터프레임
        district (str, optional): 자치구 필터 (예: '종로구', '강남구')
        parking_type (str, optional): 주차장 유형 ('노외 주차장', '노상 주차장')
        pay_yn (str, optional): 유료/무료 ('유료', '무료')

    Returns:
        pd.DataFrame: 최신 시점 필터링된 주차장 데이터
    """
    if df is None:
        df = load_data()

    latest_time = df['수집시간'].max()
    latest_df = df[df['수집시간'] == latest_time].copy()

    # 필터 적용
    if district and district != 'all':
        latest_df = latest_df[latest_df['구'].str.contains(district, na=False)]

    if parking_type and parking_type != 'all':
        latest_df = latest_df[latest_df['PRK_TYPE_NM'].str.contains(parking_type, na=False)]

    if pay_yn and pay_yn != 'all':
        latest_df = latest_df[latest_df['PAY_YN_NM'] == pay_yn]

    return latest_df.reset_index(drop=True)


def get_district_summary(df=None):
    """
    서울시 23개 자치구별 주차 통계를 집계하여 추출합니다.

    Returns:
        pd.DataFrame: 구별 주차장 수, 총면수, 주차대수, 남은자리, 평균이용률, 만차개소 수
    """
    latest = get_latest_status(df)

    summary = latest.groupby('구').agg(
        주차장수=('PKLT_CD', 'count'),
        총주차면수=('TPKCT', 'sum'),
        현재주차대수=('NOW_PRK_VHCL_CNT', 'sum'),
        총남은자리=('남은자리', 'sum'),
        평균이용률=('주차이용률', 'mean'),
        만차주차장수=('혼잡도_등급', lambda x: (x == '만차').sum())
    ).reset_index()

    summary['평균이용률'] = summary['평균이용률'].round(1)
    summary = summary.sort_values(by='평균이용률', ascending=False).reset_index(drop=True)
    return summary


def get_time_series_trend(df=None, district=None, lot_name=None):
    """
    수집시간(10:39 ~ 14:39, 49개 시점)에 따른 시계열 주차 이용률 추이를 추출합니다.

    Args:
        df (pd.DataFrame, optional): 데이터프레임
        district (str, optional): 특정 구 기준 필터
        lot_name (str, optional): 특정 주차장명 기준 필터

    Returns:
        pd.DataFrame: 시간대별 평균이용률, 총주차대수, 총남은자리
    """
    if df is None:
        df = load_data()

    filtered = df.copy()
    if district and district != 'all':
        filtered = filtered[filtered['구'].str.contains(district, na=False)]

    if lot_name:
        filtered = filtered[filtered['PKLT_NM'].str.contains(lot_name, na=False)]

    trend = filtered.groupby('수집시간').agg(
        평균이용률=('주차이용률', 'mean'),
        현재주차대수=('NOW_PRK_VHCL_CNT', 'sum'),
        총남은자리=('남은자리', 'sum'),
        모니터링수=('PKLT_CD', 'count')
    ).reset_index()

    trend['평균이용률'] = trend['평균이용률'].round(2)
    # 시간 순서 정렬
    trend = trend.sort_values(by='수집시간').reset_index(drop=True)
    # 간단한 시간 라벨(HH:MM) 추가
    trend['시간'] = trend['수집시간'].str.extract(r'(\d{2}:\d{2}):\d{2}')
    return trend


def get_top_congested(n=10, df=None, district=None):
    """
    최신 시점 기준 주차 이용률이 가장 높은 혼잡/만차 주차장 Top N을 추출합니다.
    """
    latest = get_latest_status(df, district=district)
    sorted_df = latest.sort_values(by=['주차이용률', 'NOW_PRK_VHCL_CNT'], ascending=[False, False])
    cols = ['PKLT_CD', 'PKLT_NM', '구', 'ADDR', 'TPKCT', 'NOW_PRK_VHCL_CNT', '남은자리', '주차이용률', '혼잡도_등급', 'PRK_TYPE_NM']
    return sorted_df[cols].head(n).reset_index(drop=True)


def get_top_available(n=10, df=None, district=None):
    """
    최신 시점 기준 남은 자리가 가장 많은 여유 주차장 Top N을 추출합니다.
    """
    latest = get_latest_status(df, district=district)
    sorted_df = latest.sort_values(by=['남은자리', '주차이용률'], ascending=[False, True])
    cols = ['PKLT_CD', 'PKLT_NM', '구', 'ADDR', 'TPKCT', 'NOW_PRK_VHCL_CNT', '남은자리', '주차이용률', '혼잡도_등급', 'PRK_TYPE_NM']
    return sorted_df[cols].head(n).reset_index(drop=True)


def get_type_summary(df=None):
    """
    주차장 유형(노외/노상) 및 과금(유료/무료)별 통계 요약을 추출합니다.
    """
    latest = get_latest_status(df)

    by_type = latest.groupby('PRK_TYPE_NM').agg(
        개소수=('PKLT_CD', 'count'),
        총면수=('TPKCT', 'sum'),
        현재주차수=('NOW_PRK_VHCL_CNT', 'sum'),
        남은자리=('남은자리', 'sum'),
        평균이용률=('주차이용률', 'mean')
    ).reset_index()
    by_type['평균이용률'] = by_type['평균이용률'].round(1)

    by_pay = latest.groupby('PAY_YN_NM').agg(
        개소수=('PKLT_CD', 'count'),
        총면수=('TPKCT', 'sum'),
        현재주차수=('NOW_PRK_VHCL_CNT', 'sum'),
        남은자리=('남은자리', 'sum'),
        평균이용률=('주차이용률', 'mean')
    ).reset_index()
    by_pay['평균이용률'] = by_pay['평균이용률'].round(1)

    return {
        'by_type': by_type,
        'by_pay': by_pay
    }


def search_parking_lots(query=None, district=None, min_available=None, max_rate=None,
                        parking_type=None, pay_yn=None, sort_by='남은자리_내림차순', df=None):
    """
    다양한 조건으로 주차장을 필터링하여 검색 결과를 추출합니다.

    Args:
        query (str): 주차장명 또는 주소 키워드
        district (str): 자치구명
        min_available (int): 최소 남은자리 수
        max_rate (float): 최대 주차이용률(%)
        parking_type (str): 주차장 유형
        pay_yn (str): 유/무료 구분
        sort_by (str): 정렬 방식 ('남은자리_내림차순', '이용률_오름차순', '총면수_내림차순')
    """
    result = get_latest_status(df)

    if query:
        q = str(query).strip()
        mask = result['PKLT_NM'].str.contains(q, case=False, regex=False, na=False) | result['ADDR'].str.contains(q, case=False, regex=False, na=False)
        result = result[mask]

    if district and district != 'all':
        result = result[result['구'].str.contains(district, regex=False, na=False)]

    if min_available is not None:
        result = result[result['남은자리'] >= int(min_available)]

    if max_rate is not None:
        result = result[result['주차이용률'] <= float(max_rate)]

    if parking_type and parking_type != 'all':
        result = result[result['PRK_TYPE_NM'].str.contains(parking_type, regex=False, na=False)]

    if pay_yn and pay_yn != 'all':
        result = result[result['PAY_YN_NM'] == pay_yn]

    if sort_by == '남은자리_내림차순':
        result = result.sort_values(by='남은자리', ascending=False)
    elif sort_by == '이용률_오름차순':
        result = result.sort_values(by='주차이용률', ascending=True)
    elif sort_by == '총면수_내림차순':
        result = result.sort_values(by='TPKCT', ascending=False)
    elif sort_by == '혼잡도_내림차순':
        result = result.sort_values(by='주차이용률', ascending=False)

    return result.reset_index(drop=True)


def get_parking_lot_history(lot_identifier, df=None):
    """
    특정 주차장의 시간대별(10:39 ~ 14:39) 상태 변화 이력을 추출합니다.

    Args:
        lot_identifier (str/int): 주차장 코드(PKLT_CD) 또는 주차장명(PKLT_NM)
    """
    if df is None:
        df = load_data()

    str_id = str(lot_identifier).strip()
    mask = (df['PKLT_CD'].astype(str) == str_id) | (df['PKLT_NM'].str.contains(str_id, regex=False, na=False))
    matched = df[mask].copy()

    if matched.empty:
        return pd.DataFrame()

    matched = matched.sort_values(by='수집시간').reset_index(drop=True)
    cols = ['수집시간', 'PKLT_CD', 'PKLT_NM', '구', 'ADDR', 'TPKCT', 'NOW_PRK_VHCL_CNT', '남은자리', '주차이용률', '혼잡도_등급']
    return matched[cols]


def export_data(data, output_path, file_format='csv'):
    """
    추출된 데이터를 파일(CSV 또는 JSON)로 저장합니다.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if isinstance(data, dict):
        if file_format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError("딕셔너리 데이터는 JSON 형식으로 내보내기를 권장합니다.")
    elif isinstance(data, pd.DataFrame):
        if file_format == 'csv':
            data.to_csv(output_path, index=False, encoding='utf-8-sig')
        elif file_format == 'json':
            data.to_json(output_path, orient='records', force_ascii=False, indent=2)
    print(f"[OK] 데이터 내보내기 완료: {output_path}")


def print_summary_report(df=None):
    """
    터미널에 종합 현황 브리핑 리포트를 출력합니다.
    """
    if df is None:
        df = load_data()

    latest = get_latest_status(df)
    total_records = len(df)
    total_lots = len(latest)
    time_points = df['수집시간'].nunique()
    start_time = df['수집시간'].min()
    end_time = df['수집시간'].max()

    total_capacity = latest['TPKCT'].sum()
    total_parked = latest['NOW_PRK_VHCL_CNT'].sum()
    total_available = latest['남은자리'].sum()
    avg_utilization = round(latest['주차이용률'].mean(), 2)

    congested_count = len(latest[latest['혼잡도_등급'].isin(['만차', '혼잡'])])
    available_count = len(latest[latest['혼잡도_등급'] == '여유'])

    print("=" * 70)
    print("[서울시 공영주차장 실시간 누적 데이터 분석 종합 리포트]")
    print("=" * 70)
    print(f"- 전체 누적 데이터 건수   : {total_records:,} 건 ({time_points}개 시점)")
    print(f"- 데이터 수집 기간       : {start_time} ~ {end_time}")
    print(f"- 모니터링 공영주차장 수 : {total_lots} 개소 (서울시 23개 자치구)")
    print(f"- 전체 주차 수용 총면수  : {total_capacity:,} 면")
    print(f"- 현재 주차 중인 차량 수 : {total_parked:,} 대")
    print(f"- 실시간 즉시 잔여면수   : {total_available:,} 면")
    print(f"- 서울시 전체 평균 이용률: {avg_utilization}%")
    print(f"- 만차/혼잡 주차장       : {congested_count} 개소 | 여유 주차장: {available_count} 개소")
    print("-" * 70)

    print("\n[주차 이용률 상위 5개소 (가장 혼잡한 곳)]")
    top_cong = get_top_congested(5, df)
    for idx, row in top_cong.iterrows():
        print(f" {idx+1}. [{row['구']}] {row['PKLT_NM']} | 이용률: {row['주차이용률']}% (잔여: {row['남은자리']}면 / 총: {row['TPKCT']}면)")

    print("\n[잔여석 상위 5개소 (가장 주차하기 쾌적한 곳)]")
    top_avail = get_top_available(5, df)
    for idx, row in top_avail.iterrows():
        print(f" {idx+1}. [{row['구']}] {row['PKLT_NM']} | 남은자리: {row['남은자리']}면 (이용률: {row['주차이용률']}%)")

    print("\n[자치구별 주차 현황 요약 (상위 5개 구)]")
    dist_sum = get_district_summary(df)
    print(dist_sum.head(5).to_string(index=False))
    print("=" * 70)


# =============================================================================
# CLI 명령줄 인터페이스
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="서울시 공영주차장 실시간 누적 데이터 추출기")
    parser.add_argument('--summary', action='store_true', help="전체 데이터셋 요약 보고서 출력")
    parser.add_argument('--latest', action='store_true', help="최신 122개 주차장 현황 추출")
    parser.add_argument('--district', type=str, help="특정 자치구 필터 (예: 강남구, 종로구)")
    parser.add_argument('--congested', type=int, nargs='?', const=10, help="혼잡 상위 N개 주차장 추출 (기본 10개)")
    parser.add_argument('--available', type=int, nargs='?', const=10, help="여유 잔여석 상위 N개 주차장 추출 (기본 10개)")
    parser.add_argument('--trend', action='store_true', help="시간대별 평균 이용률 추이 추출")
    parser.add_argument('--history', type=str, help="특정 주차장명 또는 코드의 시계열 이력 추출")
    parser.add_argument('--search', type=str, help="주차장명 또는 주소 검색어")
    parser.add_argument('--min-avail', type=int, help="최소 잔여면수 필터")
    parser.add_argument('--export', type=str, help="결과를 저장할 파일 경로 (.csv 또는 .json)")

    args = parser.parse_args()

    # 인자가 없으면 기본 요약 보고서 출력
    if len(sys.argv) == 1:
        print_summary_report()
        return

    df = load_data()
    result_df = None

    if args.summary:
        print_summary_report(df)

    if args.latest:
        result_df = get_latest_status(df, district=args.district)
        print(f"\n[최신 주차장 현황: {len(result_df)}건]")
        print(result_df[['PKLT_NM', '구', 'TPKCT', 'NOW_PRK_VHCL_CNT', '남은자리', '주차이용률', '혼잡도_등급']].head(15).to_string())

    if args.congested:
        result_df = get_top_congested(args.congested, df, district=args.district)
        print(f"\n[혼잡 주차장 Top {args.congested}]")
        print(result_df.to_string())

    if args.available:
        result_df = get_top_available(args.available, df, district=args.district)
        print(f"\n[여유 주차장 Top {args.available}]")
        print(result_df.to_string())

    if args.trend:
        result_df = get_time_series_trend(df, district=args.district)
        print(f"\n[시간대별 이용률 추이]")
        print(result_df.head(15).to_string())

    if args.history:
        result_df = get_parking_lot_history(args.history, df)
        print(f"\n[{args.history} 시계열 이력: {len(result_df)}건]")
        print(result_df.to_string())

    if args.search:
        result_df = search_parking_lots(query=args.search, district=args.district, min_available=args.min_avail, df=df)
        print(f"\n['{args.search}' 검색 결과: {len(result_df)}건]")
        print(result_df[['PKLT_NM', '구', 'ADDR', '남은자리', '주차이용률', '혼잡도_등급']].to_string())

    if args.export and result_df is not None:
        fmt = 'json' if args.export.endswith('.json') else 'csv'
        export_data(result_df, args.export, file_format=fmt)


if __name__ == '__main__':
    main()
