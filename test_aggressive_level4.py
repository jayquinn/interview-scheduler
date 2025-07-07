#!/usr/bin/env python3
"""
공격적 Level 4 후처리 조정 테스트

개선된 설정으로 디폴트 데이터 테스트:
- 체류시간 기준: 상위 50% 또는 4시간 이상
- 개선 가능성 기준: 0.3시간
- 최대 조정 그룹: 4개
- 활동 간격 기준: 2시간
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, date
import pandas as pd
from solver.api import solve_for_days_v2
from test_app_default_data import create_app_default_data
import core

def test_aggressive_level4():
    """공격적 Level 4 후처리 조정 테스트"""
    print("🔥 공격적 Level 4 후처리 조정 테스트 시작")
    print("="*60)
    
    # 1. 디폴트 데이터 생성
    print("📊 디폴트 데이터 생성...")
    session_state = create_app_default_data()
    
    # 2. 현재 날짜 기준으로 4일 계획으로 확장
    today = datetime.now().date()
    dates = [today + timedelta(days=i) for i in range(4)]
    
    # 멀티데이트 플랜 확장 - 더 많은 지원자로 변경
    multidate_plans = {}
    job_counts = [46, 40, 33, 18]  # 각 날짜별 지원자 수
    
    for i, test_date in enumerate(dates):
        date_str = test_date.strftime("%Y-%m-%d")
        multidate_plans[date_str] = {
            "date": test_date,
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": job_counts[i] // 11 * 3},  # JOB01 비율
                {"code": "JOB02", "count": job_counts[i] // 11 * 3},  # JOB02 비율
                {"code": "JOB03", "count": job_counts[i] // 11 * 2},  # JOB03 비율
                {"code": "JOB04", "count": job_counts[i] // 11 * 2},  # JOB04 비율
                {"code": "JOB05", "count": job_counts[i] // 11 * 1},  # JOB05 비율
            ]
        }
    
    session_state['multidate_plans'] = multidate_plans
    session_state['interview_dates'] = dates
    
    # 더 큰 job_acts_map 생성
    job_acts_map = pd.DataFrame({
        "code": ["JOB01", "JOB02", "JOB03", "JOB04", "JOB05"],
        "count": [50, 50, 30, 30, 20],  # 충분한 수로 설정
        "토론면접": [True, True, True, True, True],
        "발표준비": [True, True, True, True, True], 
        "발표면접": [True, True, True, True, True]
    })
    session_state['job_acts_map'] = job_acts_map
    
    # 3. Config 빌드
    print("🔧 Config 빌드...")
    cfg = core.build_config(session_state)
    
    # 4. Level 4 OFF 테스트
    print("\n🔄 Level 4 OFF 테스트...")
    params_off = {'enable_level4': False}
    
    status_off, result_off, logs_off, limit_off = solve_for_days_v2(cfg, params_off, debug=True)
    
    # 5. Level 4 ON 테스트 (공격적 설정)
    print("\n🔥 Level 4 ON 테스트 (공격적 설정)...")
    params_on = {'enable_level4': True}
    
    status_on, result_on, logs_on, limit_on = solve_for_days_v2(cfg, params_on, debug=True)
    
    # 6. 결과 분석
    print("\n📊 결과 분석")
    print("="*60)
    
    if status_off == "SUCCESS" and status_on == "SUCCESS":
        # 체류시간 비교
        stay_times_off = analyze_stay_times_df(result_off)
        stay_times_on = analyze_stay_times_df(result_on)
        
        print(f"Level 4 OFF - 평균 체류시간: {stay_times_off['average']:.1f}시간")
        print(f"Level 4 ON  - 평균 체류시간: {stay_times_on['average']:.1f}시간")
        print(f"개선 효과: {stay_times_off['average'] - stay_times_on['average']:.1f}시간")
        
        # 날짜별 상세 분석
        print("\n📅 날짜별 체류시간 분석")
        print("-" * 50)
        
        for test_date in dates:
            date_str = test_date.strftime("%Y-%m-%d")
            
            # Level 4 OFF
            off_items = result_off[result_off['interview_date'] == date_str]
            off_stats = analyze_date_stay_times_df(off_items)
            
            # Level 4 ON
            on_items = result_on[result_on['interview_date'] == date_str]
            on_stats = analyze_date_stay_times_df(on_items)
            
            print(f"{date_str}:")
            print(f"  응시자 수: {off_stats['count']}명")
            print(f"  OFF - 평균: {off_stats['average']:.1f}h, 최대: {off_stats['max']:.1f}h")
            print(f"  ON  - 평균: {on_stats['average']:.1f}h, 최대: {on_stats['max']:.1f}h")
            print(f"  개선: {off_stats['average'] - on_stats['average']:.1f}h")
            
        # 상위 체류시간 케이스 분석
        print(f"\n📈 상위 체류시간 케이스 분석")
        print("-" * 50)
        
        top_cases_off = get_top_stay_time_cases_df(result_off, 10)
        top_cases_on = get_top_stay_time_cases_df(result_on, 10)
        
        print("Level 4 OFF - 상위 10명:")
        for i, (applicant, hours) in enumerate(top_cases_off, 1):
            print(f"  {i:2d}. {applicant}: {hours:.1f}h")
            
        print("\nLevel 4 ON - 상위 10명:")
        for i, (applicant, hours) in enumerate(top_cases_on, 1):
            print(f"  {i:2d}. {applicant}: {hours:.1f}h")
    
    else:
        print("❌ 테스트 실패")
        if status_off != "SUCCESS":
            print(f"Level 4 OFF 실패: {status_off}")
            print(f"로그: {logs_off}")
        if status_on != "SUCCESS":
            print(f"Level 4 ON 실패: {status_on}")
            print(f"로그: {logs_on}")
    
    print("\n✅ 테스트 완료")

def analyze_stay_times_df(schedule_df):
    """체류시간 분석 (DataFrame 버전)"""
    if schedule_df.empty:
        return {'average': 0, 'max': 0, 'min': 0, 'count': 0}
    
    # 지원자별 체류시간 계산
    stay_times = []
    
    for applicant_id in schedule_df['id'].unique():
        applicant_data = schedule_df[schedule_df['id'] == applicant_id]
        
        if not applicant_data.empty:
            # 모든 활동의 시작시간과 종료시간
            all_times = []
            for _, row in applicant_data.iterrows():
                for col in schedule_df.columns:
                    if col.endswith('_start') or col.endswith('_end'):
                        if pd.notna(row[col]):
                            all_times.append(pd.to_datetime(row[col]))
            
            if all_times:
                min_time = min(all_times)
                max_time = max(all_times)
                stay_hours = (max_time - min_time).total_seconds() / 3600
                stay_times.append(stay_hours)
    
    if stay_times:
        return {
            'average': sum(stay_times) / len(stay_times),
            'max': max(stay_times),
            'min': min(stay_times),
            'count': len(stay_times)
        }
    else:
        return {'average': 0, 'max': 0, 'min': 0, 'count': 0}

def analyze_date_stay_times_df(schedule_df):
    """특정 날짜의 체류시간 분석 (DataFrame 버전)"""
    return analyze_stay_times_df(schedule_df)

def get_top_stay_time_cases_df(schedule_df, top_n=10):
    """체류시간 상위 N명 추출 (DataFrame 버전)"""
    if schedule_df.empty:
        return []
    
    stay_times = []
    
    for applicant_id in schedule_df['id'].unique():
        applicant_data = schedule_df[schedule_df['id'] == applicant_id]
        
        if not applicant_data.empty:
            # 모든 활동의 시작시간과 종료시간
            all_times = []
            for _, row in applicant_data.iterrows():
                for col in schedule_df.columns:
                    if col.endswith('_start') or col.endswith('_end'):
                        if pd.notna(row[col]):
                            all_times.append(pd.to_datetime(row[col]))
            
            if all_times:
                min_time = min(all_times)
                max_time = max(all_times)
                stay_hours = (max_time - min_time).total_seconds() / 3600
                stay_times.append((applicant_id, stay_hours))
    
    # 체류시간 순으로 정렬
    stay_times.sort(key=lambda x: x[1], reverse=True)
    
    return stay_times[:top_n]

if __name__ == "__main__":
    try:
        test_aggressive_level4()
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc() 