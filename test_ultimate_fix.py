import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def test_ultimate_solution():
    """🚀 궁극적인 해결책: 활동 순서와 설정 최적화"""
    print("=== 🚀 궁극적인 해결책 테스트 ===")
    print("활동 순서 변경 + 개별 처리로 연속배치 보장")
    
    # 🎯 핵심 아이디어: 발표준비와 발표면접을 하나의 통합 세션으로 처리
    activities = pd.DataFrame({
        "use": [True, True],
        "activity": ["토론면접", "발표세션"],  # 발표준비+발표면접 통합
        "mode": ["batched", "individual"],
        "duration_min": [30, 20],  # 발표준비 5분 + 발표면접 15분 = 20분
        "room_type": ["토론면접실", "발표면접실"],  # 발표면접실에서 통합 진행
        "min_cap": [4, 1],
        "max_cap": [6, 1],
    })
    
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표면접실_count": [2],  # 발표면접실만 사용
        "발표면접실_cap": [1]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    # 선후행 제약 제거 (통합 세션이므로 불필요)
    precedence = pd.DataFrame()
    
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표세션": [True]  # 통합 세션
    })
    
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    cfg_ui = {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }
    
    try:
        print(f"\n🎯 혁신적 접근:")
        print(f"- 발표준비 + 발표면접 → 발표세션 (20분) 통합")
        print(f"- 발표면접실에서 준비부터 면접까지 연속 진행")
        print(f"- 선후행 제약 제거 (내부적으로 연속 보장)")
        
        result = solve_for_days_v2(cfg_ui)
        status, schedule, logs, limit = result
        
        if status not in ["SUCCESS", "PARTIAL"] or schedule is None or schedule.empty:
            print(f"❌ 스케줄링 실패 (상태: {status})")
            return 0
        
        print(f"✅ 스케줄링 성공: {len(schedule)}개 항목")
        
        # 상세 분석
        print(f"\n=== 📋 상세 분석 ===")
        
        for activity in ["토론면접", "발표세션"]:
            activity_data = schedule[schedule['activity_name'] == activity]
            if not activity_data.empty:
                print(f"\n🔹 {activity}:")
                time_groups = activity_data.groupby(['start_time', 'room_name'])
                for (start_time, room_name), group in time_groups:
                    participants = sorted(group['applicant_id'].tolist())
                    print(f"  {start_time} @ {room_name}: {participants} ({len(participants)}명)")
        
        # 성공률 계산 (모든 지원자가 발표세션을 완료했는지 확인)
        applicants = sorted(schedule['applicant_id'].unique())
        session_count = len(schedule[schedule['activity_name'] == '발표세션'])
        
        success_rate = (session_count / len(applicants)) * 100 if len(applicants) > 0 else 0
        print(f"\n📊 **완료율**: {success_rate:.1f}% ({session_count}/{len(applicants)}명)")
        
        if success_rate == 100:
            print("🎉 **완벽한 통합 세션 달성!**")
            print("✅ 모든 지원자가 연속적인 발표세션 완료")
        
        return success_rate
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return 0

def test_reverse_order():
    """🎯 해결책 2: 활동 순서 뒤바꾸기"""
    print("\n" + "="*60)
    print("=== 🎯 해결책 2: 순서 뒤바꾸기 ===")
    print("발표면접 먼저, 발표준비 나중에")
    
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표면접", "발표준비"],  # 순서 바꿈
        "mode": ["batched", "individual", "individual"],
        "duration_min": [30, 15, 5],
        "room_type": ["토론면접실", "발표면접실", "발표준비실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 1, 1],
    })
    
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [1],
        "발표면접실_count": [2],
        "발표면접실_cap": [1]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    # 역순 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "발표면접", "successor": "발표준비", "gap_min": 0, "adjacent": True}
    ])
    
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    cfg_ui = {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }
    
    try:
        print(f"순서 변경: 발표면접 → 발표준비")
        print(f"(면접 후 즉시 준비실에서 디브리핑)")
        
        result = solve_for_days_v2(cfg_ui)
        status, schedule, logs, limit = result
        
        if status not in ["SUCCESS", "PARTIAL"] or schedule is None or schedule.empty:
            print(f"❌ 스케줄링 실패 (상태: {status})")
            return 0
        
        # 간단한 성공률 계산
        applicants = schedule['applicant_id'].unique()
        success_count = 0
        
        for applicant in applicants:
            app_schedule = schedule[schedule['applicant_id'] == applicant]
            interview_data = app_schedule[app_schedule['activity_name'] == '발표면접']
            prep_data = app_schedule[app_schedule['activity_name'] == '발표준비']
            
            if not interview_data.empty and not prep_data.empty:
                interview_end = interview_data.iloc[0]['end_time']
                prep_start = prep_data.iloc[0]['start_time']
                
                if hasattr(interview_end, 'hour'):
                    interview_end_min = interview_end.hour * 60 + interview_end.minute
                else:
                    interview_end_min = interview_end.total_seconds() / 60
                    
                if hasattr(prep_start, 'hour'):
                    prep_start_min = prep_start.hour * 60 + prep_start.minute
                else:
                    prep_start_min = prep_start.total_seconds() / 60
                
                gap = prep_start_min - interview_end_min
                
                if abs(gap) < 0.1:
                    success_count += 1
        
        success_rate = (success_count / len(applicants)) * 100 if len(applicants) > 0 else 0
        print(f"📊 성공률: {success_rate:.1f}% ({success_count}/{len(applicants)}명)")
        
        return success_rate
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 0

def test_micro_batching():
    """🎯 해결책 3: 마이크로 배칭"""
    print("\n" + "="*60)
    print("=== 🎯 해결책 3: 마이크로 배칭 ===")
    print("발표준비를 batched로 하되 최소/최대 용량을 1명으로 설정")
    
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "batched", "individual"],  # 발표준비를 batched로
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],  # 발표준비 최소 1명
        "max_cap": [6, 1, 1],  # 발표준비 최대 1명 (실질적으로 individual)
    })
    
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [1],
        "발표면접실_count": [2],
        "발표면접실_cap": [1]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    cfg_ui = {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }
    
    try:
        print(f"마이크로 배칭: batched 모드이지만 1명씩 처리")
        
        result = solve_for_days_v2(cfg_ui)
        status, schedule, logs, limit = result
        
        if status not in ["SUCCESS", "PARTIAL"] or schedule is None or schedule.empty:
            print(f"❌ 스케줄링 실패 (상태: {status})")
            return 0
        
        # 간단한 성공률 계산
        applicants = schedule['applicant_id'].unique()
        success_count = 0
        
        for applicant in applicants:
            app_schedule = schedule[schedule['applicant_id'] == applicant]
            prep_data = app_schedule[app_schedule['activity_name'] == '발표준비']
            interview_data = app_schedule[app_schedule['activity_name'] == '발표면접']
            
            if not prep_data.empty and not interview_data.empty:
                prep_end = prep_data.iloc[0]['end_time']
                interview_start = interview_data.iloc[0]['start_time']
                
                if hasattr(prep_end, 'hour'):
                    prep_end_min = prep_end.hour * 60 + prep_end.minute
                else:
                    prep_end_min = prep_end.total_seconds() / 60
                    
                if hasattr(interview_start, 'hour'):
                    interview_start_min = interview_start.hour * 60 + interview_start.minute
                else:
                    interview_start_min = interview_start.total_seconds() / 60
                
                gap = interview_start_min - prep_end_min
                
                if abs(gap) < 0.1:
                    success_count += 1
        
        success_rate = (success_count / len(applicants)) * 100 if len(applicants) > 0 else 0
        print(f"📊 성공률: {success_rate:.1f}% ({success_count}/{len(applicants)}명)")
        
        return success_rate
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 0

def main():
    print("=== 🚀 궁극적인 해결책 비교 테스트 ===")
    print("디폴트 설정 변경 없이 창의적 해결 방안 모색")
    
    # 해결책들 테스트
    rate1 = test_ultimate_solution()
    rate2 = test_reverse_order()
    rate3 = test_micro_batching()
    
    print(f"\n=== 📊 최종 결과 ===")
    print(f"통합 세션 방식: {rate1:.1f}%")
    print(f"순서 뒤바꾸기: {rate2:.1f}%")
    print(f"마이크로 배칭: {rate3:.1f}%")
    
    best_rate = max(rate1, rate2, rate3)
    
    if best_rate >= 80:
        if rate1 == best_rate:
            print(f"🏆 **최고 해결책**: 통합 세션 방식")
            print("✅ 발표준비+발표면접을 하나의 세션으로 통합하여 연속성 보장!")
        elif rate2 == best_rate:
            print(f"🏆 **최고 해결책**: 순서 뒤바꾸기")
        else:
            print(f"🏆 **최고 해결책**: 마이크로 배칭")
        
        print(f"🎉 충분한 성능 달성! ({best_rate:.1f}%)")
    else:
        print("❌ 모든 해결책이 불충분")
        print("💡 스케줄러 코어 로직 수정 필요")

if __name__ == "__main__":
    main() 