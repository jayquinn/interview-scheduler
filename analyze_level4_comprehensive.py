#!/usr/bin/env python3
"""
Level 4 후처리 조정 상세 분석 스크립트
- 날짜별 체류 시간 통계 분석
- Level 4 조정 전후 비교
- 개선 효과 정량화
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import pandas as pd
from solver.api import solve_for_days_v2

def create_default_cfg_ui():
    """내부 디폴트 데이터 생성 (app.py 스타일)"""
    import pandas as pd
    from datetime import date, time
    
    # 현재 날짜 기준으로 4일간 일정 생성
    current_date = datetime.now().date()
    dates = [current_date + timedelta(days=i) for i in range(4)]
    
    # 활동 설정 (UI 디폴트와 동일)
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 선후행 제약 (UI 디폴트와 동일)
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 운영 시간 (UI 디폴트와 동일)
    oper_start_time = time(9, 0)
    oper_end_time = time(17, 30)
    
    # 방 템플릿 (UI 디폴트와 동일)
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 멀티데이트 플랜 생성 (UI 디폴트와 동일)
    multidate_plans = {}
    
    # 첫 번째 날짜
    multidate_plans[dates[0].strftime('%Y-%m-%d')] = {
        "date": dates[0],
        "enabled": True,
        "jobs": [
            {"code": "JOB01", "count": 23},
            {"code": "JOB02", "count": 23}
        ]
    }
    
    # 두 번째 날짜
    multidate_plans[dates[1].strftime('%Y-%m-%d')] = {
        "date": dates[1],
        "enabled": True,
        "jobs": [
            {"code": "JOB03", "count": 20},
            {"code": "JOB04", "count": 20}
        ]
    }
    
    # 세 번째 날짜
    multidate_plans[dates[2].strftime('%Y-%m-%d')] = {
        "date": dates[2],
        "enabled": True,
        "jobs": [
            {"code": "JOB05", "count": 12},
            {"code": "JOB06", "count": 15},
            {"code": "JOB07", "count": 6}
        ]
    }
    
    # 네 번째 날짜
    multidate_plans[dates[3].strftime('%Y-%m-%d')] = {
        "date": dates[3],
        "enabled": True,
        "jobs": [
            {"code": "JOB08", "count": 6},
            {"code": "JOB09", "count": 6},
            {"code": "JOB10", "count": 3},
            {"code": "JOB11", "count": 3}
        ]
    }
    
    # 방 계획 생성
    final_plan_dict = {}
    for rt, values in room_template.items():
        final_plan_dict[f"{rt}_count"] = values['count']
        final_plan_dict[f"{rt}_cap"] = values['cap']
    room_plan = pd.DataFrame([final_plan_dict])
    
    # 운영 시간 생성
    oper_window_dict = {
        "start_time": oper_start_time.strftime("%H:%M"),
        "end_time": oper_end_time.strftime("%H:%M")
    }
    oper_window = pd.DataFrame([oper_window_dict])
    
    # 직무별 활동 매핑 (UI 디폴트와 동일)
    job_acts_data = []
    
    # 모든 직무 코드 수집
    all_job_codes = set()
    for plan in multidate_plans.values():
        for job in plan["jobs"]:
            all_job_codes.add(job["code"])
    
    # 각 직무별 총 인원 계산
    job_totals = {}
    for job_code in all_job_codes:
        total = 0
        for plan in multidate_plans.values():
            for job in plan["jobs"]:
                if job["code"] == job_code:
                    total += job["count"]
        job_totals[job_code] = total
    
    # 직무별 활동 매핑 생성
    for job_code in sorted(all_job_codes):
        job_acts_data.append({
            "code": job_code,
            "count": job_totals[job_code],
            "토론면접": True,
            "발표준비": True,
            "발표면접": True
        })
    
    job_acts_map = pd.DataFrame(job_acts_data)
    
    # 세션 상태 시뮬레이션
    session_state = {
        "activities": activities,
        "precedence": precedence,
        "oper_start_time": oper_start_time,
        "oper_end_time": oper_end_time,
        "room_template": room_template,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "job_acts_map": job_acts_map,
        "multidate_plans": multidate_plans,
        "group_min_size": 4,
        "group_max_size": 6,
        "global_gap_min": 5,
        "max_stay_hours": 5,
        "interview_dates": dates
    }
    
    # core.build_config 호출
    import core
    cfg = core.build_config(session_state)
    
    return cfg

def calculate_stay_time_from_df(df, applicant_id):
    """DataFrame에서 특정 지원자의 체류 시간 계산"""
    if df is None or df.empty:
        return 0
    
    # 해당 지원자의 활동들만 필터링
    if 'id' in df.columns:
        applicant_activities = df[df['id'] == applicant_id]
    elif 'applicant_id' in df.columns:
        applicant_activities = df[df['applicant_id'] == applicant_id]
    else:
        return 0
    
    if applicant_activities.empty:
        return 0
    
    # 시간을 분으로 변환
    def time_to_minutes(time_val):
        if isinstance(time_val, pd.Timedelta):
            return int(time_val.total_seconds() / 60)
        elif isinstance(time_val, str):
            h, m = map(int, time_val.split(':'))
            return h * 60 + m
        else:
            return 0
    
    # 모든 활동의 시작/종료 시간 수집
    all_start_times = []
    all_end_times = []
    
    for _, row in applicant_activities.iterrows():
        if pd.notna(row['start_time']) and pd.notna(row['end_time']):
            all_start_times.append(time_to_minutes(row['start_time']))
            all_end_times.append(time_to_minutes(row['end_time']))
    
    if not all_start_times or not all_end_times:
        return 0
    
    # 최초 시작 시간부터 최종 종료 시간까지의 차이
    start_minutes = min(all_start_times)
    end_minutes = max(all_end_times)
    
    return (end_minutes - start_minutes) / 60.0  # 시간 단위로 반환

def analyze_schedule_dataframe(df):
    """스케줄 DataFrame 분석"""
    analysis = {}
    
    if df is None or df.empty:
        return analysis
    
    # 디버깅: DataFrame 구조 확인
    print(f"DataFrame columns: {df.columns.tolist()}")
    print(f"DataFrame shape: {df.shape}")
    if not df.empty:
        print(f"First few rows:\n{df.head()}")
    
    # 날짜별로 그룹화
    for date_str, date_group in df.groupby('interview_date'):
        date_analysis = {
            'total_applicants': 0,
            'stay_times': [],
            'avg_stay_time': 0,
            'min_stay_time': 0,
            'max_stay_time': 0,
            'successful_schedules': 1
        }
        
        # 각 지원자별 체류 시간 계산
        # 'id' 컬럼 확인
        if 'id' in date_group.columns:
            unique_applicants = date_group['id'].unique()
        elif 'applicant_id' in date_group.columns:
            unique_applicants = date_group['applicant_id'].unique()
        else:
            print(f"Available columns: {date_group.columns.tolist()}")
            continue
        
        stay_times = []
        
        for applicant_id in unique_applicants:
            stay_time = calculate_stay_time_from_df(date_group, applicant_id)
            if stay_time > 0:
                stay_times.append(stay_time)
        
        if stay_times:
            date_analysis['total_applicants'] = len(stay_times)
            date_analysis['stay_times'] = stay_times
            date_analysis['avg_stay_time'] = sum(stay_times) / len(stay_times)
            date_analysis['min_stay_time'] = min(stay_times)
            date_analysis['max_stay_time'] = max(stay_times)
        
        analysis[date_str] = date_analysis
    
    return analysis

def main():
    print("🔍 Level 4 후처리 조정 상세 분석 시작")
    print("=" * 50)
    
    # 디폴트 데이터 생성
    print("📊 디폴트 데이터 생성 중...")
    cfg = create_default_cfg_ui()
    
    print(f"✅ 디폴트 데이터 생성 완료")
    print(f"  - 총 137명 지원자 (JOB01~JOB11)")
    print(f"  - 4일간 스케줄링 계획")
    print(f"  - 활동: 서류확인, 인성면접, 발표준비+발표면접, 토론면접")
    print()
    
    # 파라미터 설정 (UI 디폴트와 동일)
    params_without_level4 = {
        "max_stay_hours": 5,
        "enable_level4_adjustment": False
    }
    
    params_with_level4 = {
        "max_stay_hours": 5,
        "enable_level4_adjustment": True
    }
    
    print("🔄 Level 4 후처리 조정 OFF 상태로 스케줄링...")
    
    # Level 4 조정 없이 스케줄링
    try:
        status_without, df_without, logs_without, limit_without = solve_for_days_v2(
            cfg, params_without_level4, debug=False
        )
        print(f"  결과: {status_without}")
        if df_without is not None:
            print(f"  스케줄 건수: {len(df_without)}")
        else:
            print("  ❌ 스케줄링 실패")
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        df_without = None
    
    print("\n🔄 Level 4 후처리 조정 ON 상태로 스케줄링...")
    
    # Level 4 조정 포함 스케줄링
    try:
        status_with, df_with, logs_with, limit_with = solve_for_days_v2(
            cfg, params_with_level4, debug=False
        )
        print(f"  결과: {status_with}")
        if df_with is not None:
            print(f"  스케줄 건수: {len(df_with)}")
        else:
            print("  ❌ 스케줄링 실패")
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        df_with = None
    
    print("\n📈 결과 분석")
    print("=" * 50)
    
    # 결과 분석
    analysis_without = analyze_schedule_dataframe(df_without)
    analysis_with = analyze_schedule_dataframe(df_with)
    
    print("\n📊 날짜별 체류 시간 통계 (Level 4 조정 OFF)")
    print("-" * 50)
    
    total_without = {'applicants': 0, 'total_stay_time': 0}
    for date_str, data in analysis_without.items():
        if data['successful_schedules'] > 0:
            print(f"🗓️  {date_str}:")
            print(f"    응시자 수: {data['total_applicants']}명")
            print(f"    평균 체류시간: {data['avg_stay_time']:.1f}시간")
            print(f"    최소 체류시간: {data['min_stay_time']:.1f}시간")
            print(f"    최대 체류시간: {data['max_stay_time']:.1f}시간")
            print()
            
            total_without['applicants'] += data['total_applicants']
            total_without['total_stay_time'] += sum(data['stay_times'])
    
    print("\n📊 날짜별 체류 시간 통계 (Level 4 조정 ON)")
    print("-" * 50)
    
    total_with = {'applicants': 0, 'total_stay_time': 0}
    for date_str, data in analysis_with.items():
        if data['successful_schedules'] > 0:
            print(f"🗓️  {date_str}:")
            print(f"    응시자 수: {data['total_applicants']}명")
            print(f"    평균 체류시간: {data['avg_stay_time']:.1f}시간")
            print(f"    최소 체류시간: {data['min_stay_time']:.1f}시간")
            print(f"    최대 체류시간: {data['max_stay_time']:.1f}시간")
            print()
            
            total_with['applicants'] += data['total_applicants']
            total_with['total_stay_time'] += sum(data['stay_times'])
    
    print("\n📈 Level 4 후처리 조정 효과 분석")
    print("-" * 50)
    
    if total_without['applicants'] > 0 and total_with['applicants'] > 0:
        avg_without = total_without['total_stay_time'] / total_without['applicants']
        avg_with = total_with['total_stay_time'] / total_with['applicants']
        improvement = avg_without - avg_with
        improvement_pct = (improvement / avg_without) * 100
        
        print(f"전체 평균 체류시간:")
        print(f"  Level 4 조정 OFF: {avg_without:.1f}시간")
        print(f"  Level 4 조정 ON:  {avg_with:.1f}시간")
        print(f"  개선 효과: {improvement:.1f}시간 ({improvement_pct:.1f}% 감소)")
        print()
        
        # 날짜별 개선 효과 상세 분석
        print("📊 날짜별 개선 효과:")
        for date_str in analysis_without.keys():
            if (analysis_without[date_str]['successful_schedules'] > 0 and 
                analysis_with[date_str]['successful_schedules'] > 0):
                
                avg_before = analysis_without[date_str]['avg_stay_time']
                avg_after = analysis_with[date_str]['avg_stay_time']
                improvement = avg_before - avg_after
                improvement_pct = (improvement / avg_before) * 100 if avg_before > 0 else 0
                
                print(f"  {date_str}: {improvement:.1f}시간 ({improvement_pct:.1f}% 감소)")
    
    print("\n🔍 Level 4 조정 로직 분석")
    print("-" * 50)
    
    # Level 4 조정 로직 확인
    print("현재 Level 4 조정 기준:")
    print("1. 체류시간 기준: 상위 30% 또는 6시간 이상")
    print("2. 개선 가능성: 0.5시간 이상 (활동 간격 4시간 이상)")
    print("3. 최대 조정 그룹: 2개 (안전성 고려)")
    print("4. 적용 범위: 전체 날짜 통합 기준")
    print()
    
    print("📋 개선 제안:")
    print("1. 날짜별 개별 기준 적용 검토")
    print("2. 최대 조정 그룹 수 증가 검토") 
    print("3. 더 공격적인 체류시간 기준 검토")
    print("4. 개선 임계값 조정 검토")
    
    # 로그 출력
    if 'logs_with' in locals() and logs_with:
        print("\n📝 Level 4 조정 로그:")
        print("-" * 50)
        print(logs_with[-1000:])  # 마지막 1000자만 출력

if __name__ == "__main__":
    main() 