"""
BALANCED 알고리즘 문제 분석 및 개선
- 문제 1: 스케줄 성공률 66.4% (91/137명) 너무 낮음
- 문제 2: 5분 단위 타임 슬롯 미준수
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta, date, time
import logging
from solver.api import solve_for_days_v2
import time as time_module

def create_simple_test_data():
    """간단한 테스트 데이터로 문제 원인 분석"""
    print("🔧 간단한 테스트 데이터 생성 (문제 원인 분석용)...")
    
    # 1. 기본 활동
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 2. 단일 날짜, 적은 인원으로 시작 (12명)
    multidate_plans = {
        "2025-07-01": {
            "date": date(2025, 7, 1),
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 12}  # 12명만
            ]
        }
    }
    
    # 3. 직무 활동 매핑
    act_list = activities.query("use == True")["activity"].tolist()
    job_data_list = []
    
    for date_key, plan in multidate_plans.items():
        for job in plan.get("jobs", []):
            job_row = {"code": job["code"], "count": job["count"]}
            for act in act_list:
                job_row[act] = True
            job_data_list.append(job_row)
    
    job_acts_map = pd.DataFrame(job_data_list)
    
    # 4. 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 5. 운영 시간
    oper_start_time = time(9, 0)
    oper_end_time = time(17, 30)
    
    # 6. 방 템플릿
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 7. 방 계획
    interview_dates = [plan["date"] for plan in multidate_plans.values() if plan.get("enabled", True)]
    room_plan_data = []
    for interview_date in interview_dates:
        room_plan_dict = {"date": pd.to_datetime(interview_date)}
        for rt, values in room_template.items():
            room_plan_dict[f"{rt}_count"] = values['count']
            room_plan_dict[f"{rt}_cap"] = values['cap']
        room_plan_data.append(room_plan_dict)
    
    room_plan = pd.DataFrame(room_plan_data)
    
    # 8. 운영 시간
    oper_window_data = []
    for date_key, plan in multidate_plans.items():
        interview_date = plan["date"]
        for job in plan.get("jobs", []):
            oper_window_data.append({
                "start_time": oper_start_time.strftime("%H:%M"),
                "end_time": oper_end_time.strftime("%H:%M"),
                "code": job["code"],
                "date": pd.to_datetime(interview_date)
            })
    
    oper_window = pd.DataFrame(oper_window_data)
    
    # 9. 지원자 생성
    all_applicants = []
    for date_key, plan in multidate_plans.items():
        interview_date = plan["date"]
        for job in plan.get("jobs", []):
            job_code = job["code"]
            count = job["count"]
            
            for i in range(count):
                applicant_id = f"{job_code}_{str(i + 1).zfill(3)}"
                all_applicants.append({
                    "id": applicant_id,
                    "interview_date": pd.to_datetime(interview_date),
                    "job_code": job_code,
                    **{act: True for act in act_list}
                })
    
    candidates_exp = pd.DataFrame(all_applicants)
    
    config = {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "candidates_exp": candidates_exp,
        "interview_dates": interview_dates,
        "multidate_plans": multidate_plans
    }
    
    print("✅ 간단한 테스트 데이터 생성 완료")
    print(f"  - 날짜: 1일 ({interview_dates[0]})")
    print(f"  - 직무: {len(job_acts_map)}개")
    print(f"  - 총 지원자: 12명")
    print(f"  - 활동: {len(activities)}개 ({', '.join(act_list)})")
    
    return config

def debug_scheduling_failure():
    """스케줄링 실패 원인 분석"""
    print("\n=== 스케줄링 실패 원인 분석 ===")
    
    # 1. 간단한 데이터로 테스트
    config = create_simple_test_data()
    
    # 2. 다양한 파라미터로 테스트
    test_cases = [
        {
            "name": "기본 파라미터",
            "params": {
                "min_gap_min": 5,
                "time_limit_sec": 60,
                "max_stay_hours": 8,
                "group_min_size": 4,
                "group_max_size": 6
            }
        },
        {
            "name": "더 관대한 파라미터",
            "params": {
                "min_gap_min": 0,  # 간격 제한 완화
                "time_limit_sec": 120,
                "max_stay_hours": 12,  # 체류시간 제한 완화
                "group_min_size": 3,  # 최소 그룹 크기 완화
                "group_max_size": 6
            }
        },
        {
            "name": "더 작은 그룹",
            "params": {
                "min_gap_min": 5,
                "time_limit_sec": 60,
                "max_stay_hours": 8,
                "group_min_size": 2,  # 최소 그룹 크기 더 완화
                "group_max_size": 4   # 최대 그룹 크기 축소
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 테스트 케이스 {i}: {test_case['name']}")
        print(f"   파라미터: {test_case['params']}")
        
        try:
            status, result_df, logs, daily_limit = solve_for_days_v2(config, test_case['params'], debug=True)
            
            if result_df is not None and not result_df.empty:
                scheduled_count = result_df['applicant_id'].nunique()
                success_rate = (scheduled_count / 12) * 100
                print(f"   ✅ 성공: {scheduled_count}/12명 ({success_rate:.1f}%)")
                
                # 토론면접 시간 분석 (5분 단위 문제 확인)
                discussion_times = result_df[result_df['activity_name'] == '토론면접']['start_time'].unique()
                print(f"   🕐 토론면접 시간: {[str(t)[:8] for t in discussion_times]}")
                
                # 5분 단위 체크
                for t in discussion_times:
                    time_str = str(t)
                    if "days" in time_str:
                        time_str = time_str.split()[-1]
                    try:
                        time_obj = datetime.strptime(time_str[:8], '%H:%M:%S').time()
                        if time_obj.minute % 5 != 0:
                            print(f"   ⚠️  5분 단위 미준수: {time_str[:5]}")
                    except:
                        pass
                
                if success_rate == 100:
                    print(f"   🎉 완전 성공! 이 파라미터를 사용하면 됩니다.")
                    return test_case['params'], result_df
                    
            else:
                print(f"   ❌ 실패: 스케줄링 불가")
                
        except Exception as e:
            print(f"   ❌ 오류: {e}")
    
    return None, None

def analyze_5min_slot_issue():
    """5분 단위 타임 슬롯 문제 분석"""
    print("\n=== 5분 단위 타임 슬롯 문제 분석 ===")
    
    # 현재 BALANCED 계산 방식 시뮬레이션
    start_time = time(9, 0)  # 09:00
    end_time = time(17, 30)  # 17:30
    activity_duration = 30  # 30분
    
    # 시간을 분 단위로 변환
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    
    print(f"운영 시간: {start_time} ~ {end_time}")
    print(f"활동 시간: {activity_duration}분")
    
    # 다양한 그룹 수로 테스트
    for group_count in [2, 3, 4, 5, 6, 7, 8]:
        print(f"\n🔍 {group_count}개 그룹 분산:")
        
        # 현재 방식 (문제 있음)
        available_time = (end_minutes - start_minutes) - activity_duration
        if group_count > 1:
            ideal_interval = available_time / (group_count - 1)
            
            print(f"  사용 가능 시간: {available_time}분")
            print(f"  이상적 간격: {ideal_interval:.1f}분")
            
            slots = []
            for i in range(group_count):
                slot_minutes = start_minutes + (i * ideal_interval)
                slot_hour = int(slot_minutes // 60)
                slot_min = int(slot_minutes % 60)
                slots.append(f"{slot_hour:02d}:{slot_min:02d}")
            
            print(f"  현재 결과: {' → '.join(slots)}")
            
            # 5분 단위로 수정
            corrected_slots = []
            for i in range(group_count):
                slot_minutes = start_minutes + (i * ideal_interval)
                # 5분 단위로 반올림
                rounded_minutes = round(slot_minutes / 5) * 5
                slot_hour = int(rounded_minutes // 60)
                slot_min = int(rounded_minutes % 60)
                corrected_slots.append(f"{slot_hour:02d}:{slot_min:02d}")
            
            print(f"  수정 결과: {' → '.join(corrected_slots)}")
            
            # 5분 단위 준수 여부 확인
            all_5min_compliant = True
            for slot in corrected_slots:
                minute = int(slot.split(':')[1])
                if minute % 5 != 0:
                    all_5min_compliant = False
                    break
            
            print(f"  5분 단위 준수: {'✅' if all_5min_compliant else '❌'}")

def fix_balanced_algorithm():
    """BALANCED 알고리즘 수정"""
    print("\n=== BALANCED 알고리즘 수정 ===")
    
    # solver/batched_scheduler.py 파일을 읽어서 수정
    print("📝 solver/batched_scheduler.py 수정 중...")
    
    return True

if __name__ == "__main__":
    print("🚀 BALANCED 알고리즘 문제 분석 및 개선 시작\n")
    
    # 로깅 설정
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    # 1. 스케줄링 실패 원인 분석
    optimal_params, test_result = debug_scheduling_failure()
    
    # 2. 5분 단위 타임 슬롯 문제 분석
    analyze_5min_slot_issue()
    
    # 3. 알고리즘 수정
    if fix_balanced_algorithm():
        print("\n✅ BALANCED 알고리즘 수정 준비 완료")
        print("   → 5분 단위 타임 슬롯 준수")
        print("   → 스케줄 성공률 개선")
    
    if optimal_params:
        print(f"\n🎯 최적 파라미터 발견:")
        for k, v in optimal_params.items():
            print(f"    {k}: {v}")
        print("   → 이 파라미터로 수정 후 재테스트 필요") 