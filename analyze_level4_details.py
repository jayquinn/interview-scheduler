#!/usr/bin/env python3
"""
Level 4 후처리 조정 상세 분석: JOB02_013 vs JOB02_019
왜 한 지원자는 조정되고 다른 지원자는 조정되지 않았는지 분석
"""

import sys
import os
from datetime import date, timedelta
from collections import defaultdict

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solver.api import solve_for_days_v2

def analyze_level4_details():
    """Level 4 후처리 조정 상세 분석"""
    print("🔍 Level 4 후처리 조정 상세 분석 시작...")
    
    # 1. 완전한 내부 디폴트 데이터 설정
    today = date.today()
    
    multidate_plans = {
        today.strftime('%Y-%m-%d'): {
            "date": today,
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 23},
                {"code": "JOB02", "count": 23}
            ]
        },
        (today + timedelta(days=1)).strftime('%Y-%m-%d'): {
            "date": today + timedelta(days=1),
            "enabled": True,
            "jobs": [
                {"code": "JOB03", "count": 20},
                {"code": "JOB04", "count": 20}
            ]
        },
        (today + timedelta(days=2)).strftime('%Y-%m-%d'): {
            "date": today + timedelta(days=2),
            "enabled": True,
            "jobs": [
                {"code": "JOB05", "count": 12},
                {"code": "JOB06", "count": 15},
                {"code": "JOB07", "count": 6}
            ]
        },
        (today + timedelta(days=3)).strftime('%Y-%m-%d'): {
            "date": today + timedelta(days=3),
            "enabled": True,
            "jobs": [
                {"code": "JOB08", "count": 6},
                {"code": "JOB09", "count": 6},
                {"code": "JOB10", "count": 3},
                {"code": "JOB11", "count": 3}
            ]
        }
    }
    
    import pandas as pd
    
    # DataFrame으로 변환
    activities_df = pd.DataFrame([
        {"use": True, "activity": "토론면접", "mode": "batched", "duration_min": 30, "room_type": "토론면접실", "min_cap": 4, "max_cap": 8},
        {"use": True, "activity": "발표준비", "mode": "parallel", "duration_min": 5, "room_type": "발표준비실", "min_cap": 1, "max_cap": 1},
        {"use": True, "activity": "발표면접", "mode": "individual", "duration_min": 15, "room_type": "발표면접실", "min_cap": 1, "max_cap": 1}
    ])
    
    rooms_df = pd.DataFrame([
        {"use": True, "room": "토론면접실1", "type": "토론면접실", "capacity": 8},
        {"use": True, "room": "토론면접실2", "type": "토론면접실", "capacity": 8},
        {"use": True, "room": "발표준비실1", "type": "발표준비실", "capacity": 1},
        {"use": True, "room": "발표준비실2", "type": "발표준비실", "capacity": 1},
        {"use": True, "room": "발표면접실1", "type": "발표면접실", "capacity": 1},
        {"use": True, "room": "발표면접실2", "type": "발표면접실", "capacity": 1}
    ])
    
    cfg = {
        "multidate_plans": multidate_plans,
        "activities": activities_df,
        "rooms": rooms_df,
        "operating_hours": {"start": "09:00", "end": "18:00"},
        "min_gap_min": 10,
        "smart_integration": True
    }
    
    params = {
        "min_gap_min": 10,
        "time_limit_sec": 30,
        "max_stay_hours": 12,
        "group_min_size": 4,
        "group_max_size": 8
    }
    
    # 2. 스케줄링 실행
    print("🚀 스케줄링 실행...")
    status, schedule_df, logs, daily_limit = solve_for_days_v2(cfg, params=params, debug=True)
    
    if status != 'SUCCESS':
        print(f"❌ 스케줄링 실패: {status}")
        return
    
    print(f"✅ 스케줄링 성공: {len(schedule_df)}개 항목")
    
    # 3. 첫 번째 날짜 (오늘) 데이터만 분석
    first_date = today
    first_date_df = schedule_df[schedule_df['date'] == first_date].copy()
    
    print(f"\n📅 {first_date} 데이터 분석:")
    print(f"   총 스케줄 항목: {len(first_date_df)}개")
    
    # 4. JOB02_013과 JOB02_019 찾기
    job02_candidates = first_date_df[first_date_df['job_code'] == 'JOB02'].copy()
    
    target_candidates = ['JOB02_013', 'JOB02_019']
    found_candidates = []
    
    for candidate in target_candidates:
        if candidate in job02_candidates['applicant_id'].values:
            found_candidates.append(candidate)
        else:
            print(f"⚠️ {candidate} 지원자를 찾을 수 없습니다.")
    
    if not found_candidates:
        print("❌ 분석 대상 지원자들을 찾을 수 없습니다.")
        print("💡 실제 생성된 JOB02 지원자들:")
        job02_applicants = sorted(job02_candidates['applicant_id'].unique())
        for i, applicant in enumerate(job02_applicants[:10]):  # 첫 10명만 표시
            print(f"     {i+1:2d}. {applicant}")
        if len(job02_applicants) > 10:
            print(f"     ... 그 외 {len(job02_applicants) - 10}명 더")
        return
    
    # 5. 각 지원자의 스케줄 분석
    for candidate in found_candidates:
        print(f"\n👤 {candidate} 분석:")
        
        candidate_schedule = first_date_df[first_date_df['applicant_id'] == candidate].copy()
        candidate_schedule = candidate_schedule.sort_values('start_time')
        
        print(f"   활동 수: {len(candidate_schedule)}개")
        
        # 각 활동 출력
        for _, row in candidate_schedule.iterrows():
            print(f"     {row['start_time']} - {row['end_time']}: {row['activity_name']} ({row['room_name']}, 그룹: {row.get('group_id', 'N/A')})")
        
        # 체류시간 계산
        if len(candidate_schedule) > 0:
            first_start = candidate_schedule.iloc[0]['start_time']
            last_end = candidate_schedule.iloc[-1]['end_time']
            
            # 시간 파싱
            from datetime import datetime
            if isinstance(first_start, str):
                first_start = datetime.strptime(first_start, '%H:%M:%S').time()
            if isinstance(last_end, str):
                last_end = datetime.strptime(last_end, '%H:%M:%S').time()
            
            # timedelta로 변환
            first_start_td = timedelta(hours=first_start.hour, minutes=first_start.minute, seconds=first_start.second)
            last_end_td = timedelta(hours=last_end.hour, minutes=last_end.minute, seconds=last_end.second)
            
            stay_time_hours = (last_end_td - first_start_td).total_seconds() / 3600
            
            print(f"   체류시간: {stay_time_hours:.1f}시간 ({first_start} ~ {last_end})")
            
            # 개선 가능성 계산
            if len(candidate_schedule) >= 2:
                first_end = candidate_schedule.iloc[0]['end_time']
                last_start = candidate_schedule.iloc[-1]['start_time']
                
                if isinstance(first_end, str):
                    first_end = datetime.strptime(first_end, '%H:%M:%S').time()
                if isinstance(last_start, str):
                    last_start = datetime.strptime(last_start, '%H:%M:%S').time()
                
                first_end_td = timedelta(hours=first_end.hour, minutes=first_end.minute, seconds=first_end.second)
                last_start_td = timedelta(hours=last_start.hour, minutes=last_start.minute, seconds=last_start.second)
                
                gap_hours = (last_start_td - first_end_td).total_seconds() / 3600
                improvement_potential = max(0.0, gap_hours - 2.0)
                
                print(f"   활동 간격: {gap_hours:.1f}시간")
                print(f"   개선 가능성: {improvement_potential:.1f}시간")
                
                # Level 4 조정 조건 확인
                is_problem_case = stay_time_hours >= 6.0 or improvement_potential > 0.5
                print(f"   문제 케이스 여부: {is_problem_case}")
                print(f"     - 체류시간 6시간 이상: {stay_time_hours >= 6.0}")
                print(f"     - 개선 가능성 0.5시간 이상: {improvement_potential > 0.5}")
    
    # 6. 전체 체류시간 분포 분석
    print(f"\n📊 전체 체류시간 분포 분석:")
    
    # 지원자별 체류시간 계산
    stay_times = []
    for applicant in first_date_df['applicant_id'].unique():
        if applicant.startswith('dummy'):
            continue
            
        applicant_schedule = first_date_df[first_date_df['applicant_id'] == applicant].copy()
        applicant_schedule = applicant_schedule.sort_values('start_time')
        
        if len(applicant_schedule) > 0:
            first_start = applicant_schedule.iloc[0]['start_time']
            last_end = applicant_schedule.iloc[-1]['end_time']
            
            # 시간 파싱
            from datetime import datetime
            if isinstance(first_start, str):
                first_start = datetime.strptime(first_start, '%H:%M:%S').time()
            if isinstance(last_end, str):
                last_end = datetime.strptime(last_end, '%H:%M:%S').time()
            
            # timedelta로 변환
            first_start_td = timedelta(hours=first_start.hour, minutes=first_start.minute, seconds=first_start.second)
            last_end_td = timedelta(hours=last_end.hour, minutes=last_end.minute, seconds=last_end.second)
            
            stay_time_hours = (last_end_td - first_start_td).total_seconds() / 3600
            stay_times.append((applicant, stay_time_hours))
    
    # 체류시간 순으로 정렬
    stay_times.sort(key=lambda x: x[1], reverse=True)
    
    print(f"   전체 지원자 수: {len(stay_times)}명")
    print(f"   평균 체류시간: {sum(x[1] for x in stay_times) / len(stay_times):.1f}시간")
    print(f"   최대 체류시간: {max(x[1] for x in stay_times):.1f}시간")
    print(f"   최소 체류시간: {min(x[1] for x in stay_times):.1f}시간")
    
    # 상위 30% 임계값 계산
    threshold_30percent = stay_times[int(len(stay_times) * 0.3)][1]
    problem_threshold = max(6.0, threshold_30percent)
    
    print(f"   상위 30% 임계값: {threshold_30percent:.1f}시간")
    print(f"   문제 케이스 임계값: {problem_threshold:.1f}시간")
    
    # 상위 체류시간 지원자들
    print(f"\n🔥 상위 체류시간 지원자들:")
    for i, (applicant, stay_time) in enumerate(stay_times[:10]):
        is_problem = stay_time >= problem_threshold
        marker = "🎯" if is_problem else "  "
        print(f"   {marker} {i+1:2d}. {applicant}: {stay_time:.1f}시간")

if __name__ == "__main__":
    analyze_level4_details() 