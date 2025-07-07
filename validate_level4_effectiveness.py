#!/usr/bin/env python3
"""
Level 4 후처리 조정 효과 검증

공격적 설정의 실제 효과를 정확히 측정합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, date
import pandas as pd
from solver.api import solve_for_days_v2
from test_app_default_data import create_app_default_data
import core

def validate_level4_effectiveness():
    """Level 4 조정 효과 정확 검증"""
    print("🔍 Level 4 후처리 조정 효과 검증")
    print("="*60)
    
    # 1. 단일 날짜로 명확한 테스트
    print("📊 단일 날짜 테스트로 명확한 비교...")
    session_state = create_app_default_data()
    
    today = datetime.now().date()
    date_str = today.strftime("%Y-%m-%d")
    
    # 적절한 수의 지원자로 설정 (Level 4 효과를 보기 위해)
    multidate_plans = {
        date_str: {
            "date": today,
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 8},
                {"code": "JOB02", "count": 8},
                {"code": "JOB03", "count": 6},
                {"code": "JOB04", "count": 6},
                {"code": "JOB05", "count": 4},
            ]
        }
    }
    
    session_state['multidate_plans'] = multidate_plans
    session_state['interview_dates'] = [today]
    
    # 더 큰 job_acts_map 생성
    job_acts_map = pd.DataFrame({
        "code": ["JOB01", "JOB02", "JOB03", "JOB04", "JOB05"],
        "count": [50, 50, 30, 30, 20],
        "토론면접": [True, True, True, True, True],
        "발표준비": [True, True, True, True, True], 
        "발표면접": [True, True, True, True, True]
    })
    session_state['job_acts_map'] = job_acts_map
    
    cfg = core.build_config(session_state)
    
    # 2. Level 4 OFF 테스트
    print("\n🔄 Level 4 OFF 테스트...")
    params_off = {'enable_level4': False}
    status_off, result_off, logs_off, limit_off = solve_for_days_v2(cfg, params_off, debug=False)
    
    # 3. Level 4 ON 테스트 
    print("🔥 Level 4 ON 테스트...")
    params_on = {'enable_level4': True}
    status_on, result_on, logs_on, limit_on = solve_for_days_v2(cfg, params_on, debug=False)
    
    # 4. 상세 분석
    if status_off == "SUCCESS" and status_on == "SUCCESS":
        print("\n📊 상세 분석 결과")
        print("="*60)
        
        # Level 4 조정 로그 추출
        level4_logs = [line for line in logs_on.split('\n') if 'Level 4' in line]
        print("🔧 Level 4 조정 로그:")
        for log in level4_logs:
            if log.strip():
                print(f"  {log.strip()}")
        
        # 그룹 이동 로그 추출
        move_logs = [line for line in logs_on.split('\n') if '이동:' in line]
        print(f"\n🚚 그룹 이동 로그 ({len(move_logs)}건):")
        for log in move_logs[:10]:  # 최대 10개만 표시
            if log.strip():
                print(f"  {log.strip()}")
        if len(move_logs) > 10:
            print(f"  ... 총 {len(move_logs)}건의 이동")
        
        # DataFrame 비교
        print(f"\n📋 DataFrame 비교:")
        print(f"Level 4 OFF: {result_off.shape[0]}개 스케줄 항목")
        print(f"Level 4 ON:  {result_on.shape[0]}개 스케줄 항목")
        
        # 체류시간 분석
        stay_off = analyze_stay_times_simple(result_off)
        stay_on = analyze_stay_times_simple(result_on)
        
        print(f"\n⏱️ 체류시간 분석:")
        print(f"Level 4 OFF - 평균: {stay_off['average']:.2f}h, 최대: {stay_off['max']:.2f}h")
        print(f"Level 4 ON  - 평균: {stay_on['average']:.2f}h, 최대: {stay_on['max']:.2f}h")
        
        improvement = stay_off['average'] - stay_on['average']
        if improvement > 0:
            print(f"✅ 개선 효과: {improvement:.2f}시간 감소 ({improvement/stay_off['average']*100:.1f}%)")
        else:
            print(f"❓ 개선 효과 없음 (동일한 결과)")
        
        # 시간대별 분포 비교
        print(f"\n🕐 시간대별 활동 분포:")
        time_dist_off = analyze_time_distribution(result_off)
        time_dist_on = analyze_time_distribution(result_on)
        
        for hour in sorted(time_dist_off.keys()):
            off_count = time_dist_off.get(hour, 0)
            on_count = time_dist_on.get(hour, 0)
            change = on_count - off_count
            change_str = f"({change:+d})" if change != 0 else ""
            print(f"  {hour:02d}:00 - OFF: {off_count:2d}건, ON: {on_count:2d}건 {change_str}")
        
        # 상위 체류시간 케이스 비교
        print(f"\n📈 상위 체류시간 케이스 비교:")
        top_off = get_top_cases_simple(result_off, 5)
        top_on = get_top_cases_simple(result_on, 5)
        
        print("Level 4 OFF:")
        for i, (id, hours) in enumerate(top_off, 1):
            print(f"  {i}. {id}: {hours:.1f}h")
        
        print("Level 4 ON:")
        for i, (id, hours) in enumerate(top_on, 1):
            print(f"  {i}. {id}: {hours:.1f}h")
        
        # 최종 판정
        print(f"\n🎯 최종 판정:")
        if improvement > 0.1:
            print(f"✅ Level 4 후처리 조정이 효과적으로 작동 ({improvement:.2f}h 개선)")
        elif len(move_logs) > 0:
            print(f"⚠️ Level 4가 조정을 시도했으나 체류시간 개선 효과 미미")
            print(f"   (로그에서 {len(move_logs)}건의 그룹 이동 확인)")
        else:
            print(f"❌ Level 4 후처리 조정이 작동하지 않음")
        
        return improvement > 0, improvement
    
    else:
        print("❌ 테스트 실패")
        return False, 0

def analyze_stay_times_simple(df):
    """간단한 체류시간 분석"""
    if df.empty:
        return {'average': 0, 'max': 0, 'count': 0}
    
    stay_times = []
    
    for applicant_id in df['applicant_id'].unique():
        applicant_data = df[df['applicant_id'] == applicant_id]
        
        if not applicant_data.empty:
            all_times = []
            for _, row in applicant_data.iterrows():
                if pd.notna(row['start_time']):
                    all_times.append(row['start_time'])
                if pd.notna(row['end_time']):
                    all_times.append(row['end_time'])
            
            if all_times:
                min_time = min(all_times)
                max_time = max(all_times)
                stay_hours = (max_time - min_time).total_seconds() / 3600
                stay_times.append(stay_hours)
    
    if stay_times:
        return {
            'average': sum(stay_times) / len(stay_times),
            'max': max(stay_times),
            'count': len(stay_times)
        }
    else:
        return {'average': 0, 'max': 0, 'count': 0}

def analyze_time_distribution(df):
    """시간대별 활동 분포 분석"""
    distribution = {}
    
    for _, row in df.iterrows():
        if pd.notna(row['start_time']):
            # timedelta를 시간으로 변환
            start_hour = int(row['start_time'].total_seconds() // 3600)
            distribution[start_hour] = distribution.get(start_hour, 0) + 1
    
    return distribution

def get_top_cases_simple(df, top_n=5):
    """상위 체류시간 케이스 추출"""
    stay_times = []
    
    for applicant_id in df['applicant_id'].unique():
        applicant_data = df[df['applicant_id'] == applicant_id]
        
        if not applicant_data.empty:
            all_times = []
            for _, row in applicant_data.iterrows():
                if pd.notna(row['start_time']):
                    all_times.append(row['start_time'])
                if pd.notna(row['end_time']):
                    all_times.append(row['end_time'])
            
            if all_times:
                min_time = min(all_times)
                max_time = max(all_times)
                stay_hours = (max_time - min_time).total_seconds() / 3600
                stay_times.append((applicant_id, stay_hours))
    
    stay_times.sort(key=lambda x: x[1], reverse=True)
    return stay_times[:top_n]

if __name__ == "__main__":
    try:
        success, improvement = validate_level4_effectiveness()
        print(f"\n✅ 검증 완료: 성공={success}, 개선={improvement:.2f}h")
    except Exception as e:
        print(f"❌ 검증 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc() 