#!/usr/bin/env python3
"""
Level 4 후처리 조정 상세 분석 (간단 버전)
실제 UI 데이터를 사용하여 JOB02_013 vs JOB02_019 분석
"""

import sys
import os
import pandas as pd
from datetime import date, timedelta, datetime, time

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# UI 데이터 로드 함수
def load_ui_default_data():
    """UI 기본 데이터 로드"""
    
    # 1. 기본 활동 데이터
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [8, 1, 1]
    })
    
    # 2. 기본 방 데이터
    rooms = pd.DataFrame({
        "use": [True, True, True, True, True, True],
        "room": ["토론면접실1", "토론면접실2", "발표준비실1", "발표준비실2", "발표면접실1", "발표면접실2"],
        "type": ["토론면접실", "토론면접실", "발표준비실", "발표준비실", "발표면접실", "발표면접실"],
        "capacity": [6, 6, 1, 1, 1, 1]
    })
    
    # 3. 멀티데이트 계획 (오늘부터 4일간)
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
    
    # 4. 직무별 활동 매핑
    job_acts_map = []
    for date_key, plan in multidate_plans.items():
        for job in plan.get("jobs", []):
            job_row = {"code": job["code"], "count": job["count"]}
            for act in ["토론면접", "발표준비", "발표면접"]:
                job_row[act] = True
            job_acts_map.append(job_row)
    
    job_acts_map = pd.DataFrame(job_acts_map)
    
    # 5. 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    return {
        "activities": activities,
        "rooms": rooms,
        "multidate_plans": multidate_plans,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "operating_hours": {"start": "09:00", "end": "18:00"},
        "min_gap_min": 10,
        "smart_integration": True
    }

def analyze_level4_simple():
    """Level 4 후처리 조정 간단 분석"""
    print("🔍 Level 4 후처리 조정 간단 분석 시작...")
    
    # 1. UI 기본 데이터 로드
    ui_data = load_ui_default_data()
    
    # 2. 스케줄링 실행
    print("🚀 스케줄링 실행...")
    
    # Core 모듈을 사용한 스케줄링
    try:
        import core
        
        # 설정 빌드
        cfg = core.build_config(ui_data)
        
        # 스케줄링 실행
        params = {
            "min_gap_min": 10,
            "time_limit_sec": 30,
            "max_stay_hours": 12,
            "group_min_size": 4,
            "group_max_size": 8
        }
        
        status, schedule_df, logs = core.run_solver(cfg, params=params, debug=True)
        
        if status != 'SUCCESS':
            print(f"❌ 스케줄링 실패: {status}")
            print(f"로그: {logs}")
            return
        print(f"✅ 스케줄링 성공: {len(schedule_df)}개 항목")
        
        # 3. 첫 번째 날짜 (오늘) 데이터 분석
        today = date.today()
        today_schedules = schedule_df[schedule_df['date'] == today].copy()
        
        print(f"\n📅 {today} 데이터 분석:")
        print(f"   총 스케줄 항목: {len(today_schedules)}개")
        
        # 4. JOB02 지원자들 확인
        job02_schedules = today_schedules[today_schedules['job_code'] == 'JOB02'].copy()
        job02_candidates = sorted(job02_schedules['candidate_id'].unique())
        
        print(f"\n👥 JOB02 지원자들 ({len(job02_candidates)}명):")
        for i, candidate in enumerate(job02_candidates[:10]):  # 처음 10명만 출력
            print(f"     {i+1:2d}. {candidate}")
        if len(job02_candidates) > 10:
            print(f"     ... 그 외 {len(job02_candidates) - 10}명")
        
        # 5. 지원자별 체류시간 분석
        print(f"\n📊 체류시간 분석:")
        
        stay_time_analyses = []
        for candidate in job02_candidates:
            candidate_schedule = today_schedules[today_schedules['candidate_id'] == candidate].copy()
            candidate_schedule = candidate_schedule.sort_values('start_time')
            
            if len(candidate_schedule) > 0:
                first_start = candidate_schedule.iloc[0]['start_time']
                last_end = candidate_schedule.iloc[-1]['end_time']
                
                # 시간 파싱 및 변환
                if isinstance(first_start, str):
                    first_start = datetime.strptime(first_start, '%H:%M:%S').time()
                if isinstance(last_end, str):
                    last_end = datetime.strptime(last_end, '%H:%M:%S').time()
                
                # 체류시간 계산
                first_td = timedelta(hours=first_start.hour, minutes=first_start.minute, seconds=first_start.second)
                last_td = timedelta(hours=last_end.hour, minutes=last_end.minute, seconds=last_end.second)
                stay_time_hours = (last_td - first_td).total_seconds() / 3600
                
                # 개선 가능성 계산
                improvement_potential = 0.0
                if len(candidate_schedule) >= 2:
                    first_activity_end = candidate_schedule.iloc[0]['end_time']
                    last_activity_start = candidate_schedule.iloc[-1]['start_time']
                    
                    if isinstance(first_activity_end, str):
                        first_activity_end = datetime.strptime(first_activity_end, '%H:%M:%S').time()
                    if isinstance(last_activity_start, str):
                        last_activity_start = datetime.strptime(last_activity_start, '%H:%M:%S').time()
                    
                    first_end_td = timedelta(hours=first_activity_end.hour, minutes=first_activity_end.minute, seconds=first_activity_end.second)
                    last_start_td = timedelta(hours=last_activity_start.hour, minutes=last_activity_start.minute, seconds=last_activity_start.second)
                    
                    gap_hours = (last_start_td - first_end_td).total_seconds() / 3600
                    improvement_potential = max(0.0, gap_hours - 2.0)
                
                stay_time_analyses.append({
                    'candidate': candidate,
                    'stay_time_hours': stay_time_hours,
                    'improvement_potential': improvement_potential,
                    'first_start': first_start,
                    'last_end': last_end,
                    'schedule': candidate_schedule
                })
        
        # 체류시간 순으로 정렬
        stay_time_analyses.sort(key=lambda x: x['stay_time_hours'], reverse=True)
        
        # 6. 상위 체류시간 지원자들 출력
        print(f"\n🔥 체류시간 상위 지원자들:")
        for i, analysis in enumerate(stay_time_analyses[:10]):
            candidate = analysis['candidate']
            stay_time = analysis['stay_time_hours']
            improvement = analysis['improvement_potential']
            
            # Level 4 조정 조건 확인
            is_problem_case = stay_time >= 6.0 and improvement > 0.5
            marker = "🎯" if is_problem_case else "  "
            
            print(f"   {marker} {i+1:2d}. {candidate}: {stay_time:.1f}h (개선가능: {improvement:.1f}h)")
        
        # 7. 상위 30% 임계값 계산
        if stay_time_analyses:
            threshold_30percent = stay_time_analyses[int(len(stay_time_analyses) * 0.3)]['stay_time_hours']
            problem_threshold = max(6.0, threshold_30percent)
            
            print(f"\n📏 Level 4 조정 임계값:")
            print(f"   상위 30% 임계값: {threshold_30percent:.1f}시간")
            print(f"   문제 케이스 임계값: {problem_threshold:.1f}시간")
            
            # 문제 케이스 식별
            problem_cases = [
                analysis for analysis in stay_time_analyses 
                if analysis['stay_time_hours'] >= problem_threshold and analysis['improvement_potential'] > 0.5
            ]
            
            print(f"\n🎯 Level 4 조정 대상 지원자들 ({len(problem_cases)}명):")
            for i, analysis in enumerate(problem_cases):
                candidate = analysis['candidate']
                stay_time = analysis['stay_time_hours']
                improvement = analysis['improvement_potential']
                
                print(f"   {i+1}. {candidate}: {stay_time:.1f}h (개선가능: {improvement:.1f}h)")
                
                # 해당 지원자의 스케줄 출력
                schedule = analysis['schedule']
                print(f"      스케줄:")
                for _, row in schedule.iterrows():
                    print(f"        {row['start_time']} - {row['end_time']}: {row['activity_name']} (그룹: {row.get('group_id', 'N/A')})")
        
        # 8. 특정 지원자가 있는지 확인
        target_candidates = ['JOB02_013', 'JOB02_019']
        print(f"\n🔍 특정 지원자 확인:")
        for target in target_candidates:
            found = any(analysis['candidate'] == target for analysis in stay_time_analyses)
            if found:
                analysis = next(a for a in stay_time_analyses if a['candidate'] == target)
                stay_time = analysis['stay_time_hours']
                improvement = analysis['improvement_potential']
                is_problem = stay_time >= max(6.0, threshold_30percent) and improvement > 0.5
                
                print(f"   ✅ {target} 발견: {stay_time:.1f}h (개선가능: {improvement:.1f}h) - 조정대상: {is_problem}")
            else:
                print(f"   ❌ {target} 없음")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_level4_simple() 