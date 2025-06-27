import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def test_direct_fix():
    """🎯 직접적인 해결책: parallel → individual + 엄격한 precedence"""
    print("=== 🎯 직접적인 해결책 테스트 ===")
    print("발표준비를 individual로 변경하고 precedence 엄격 적용")
    
    # 기본 설정에서 발표준비만 individual로 변경
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "individual", "individual"],  # 발표준비를 individual로
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 1, 1],  # 발표준비도 1명으로
    })
    
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [1],  # 1명으로 변경
        "발표면접실_count": [2],
        "발표면접실_cap": [1]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    # 연속배치 제약 (gap_min=0, adjacent=True)
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
        print(f"\n설정 변경사항:")
        print(f"- 발표준비: parallel → individual")
        print(f"- 발표준비실 용량: 2명 → 1명")
        print(f"- 연속배치 제약: gap_min=0, adjacent=True")
        
        result = solve_for_days_v2(cfg_ui)
        status, schedule, logs, limit = result
        
        if status not in ["SUCCESS", "PARTIAL"] or schedule is None or schedule.empty:
            print(f"❌ 스케줄링 실패 (상태: {status})")
            return 0
        
        print(f"✅ 스케줄링 성공: {len(schedule)}개 항목")
        
        # 상세 분석
        print(f"\n=== 📋 상세 분석 ===")
        
        # 활동별 분석
        for activity in ["토론면접", "발표준비", "발표면접"]:
            activity_data = schedule[schedule['activity_name'] == activity]
            if not activity_data.empty:
                print(f"\n🔹 {activity}:")
                time_groups = activity_data.groupby(['start_time', 'room_name'])
                for (start_time, room_name), group in time_groups:
                    participants = sorted(group['applicant_id'].tolist())
                    print(f"  {start_time} @ {room_name}: {participants} ({len(participants)}명)")
        
        # 선후행 제약 분석
        print(f"\n=== 🚨 연속배치 제약 분석 ===")
        
        applicants = sorted(schedule['applicant_id'].unique())
        success_count = 0
        violations = []
        
        for applicant in applicants:
            app_schedule = schedule[schedule['applicant_id'] == applicant]
            
            prep_data = app_schedule[app_schedule['activity_name'] == '발표준비']
            interview_data = app_schedule[app_schedule['activity_name'] == '발표면접']
            
            if prep_data.empty or interview_data.empty:
                print(f"  ⚠️ {applicant}: 발표준비 또는 발표면접 데이터 없음")
                continue
            
            prep_end = prep_data.iloc[0]['end_time']
            interview_start = interview_data.iloc[0]['start_time']
            
            # 시간 차이 계산
            if hasattr(prep_end, 'hour'):
                prep_end_min = prep_end.hour * 60 + prep_end.minute
            else:
                prep_end_min = prep_end.total_seconds() / 60
                
            if hasattr(interview_start, 'hour'):
                interview_start_min = interview_start.hour * 60 + interview_start.minute
            else:
                interview_start_min = interview_start.total_seconds() / 60
            
            gap = interview_start_min - prep_end_min
            
            if abs(gap) < 0.1:  # 0분 간격 (연속배치)
                success_count += 1
                print(f"  ✅ {applicant}: 0분 간격 (연속배치)")
                print(f"     발표준비: {prep_data.iloc[0]['start_time']} ~ {prep_end}")
                print(f"     발표면접: {interview_start} ~ {interview_data.iloc[0]['end_time']}")
            else:
                violations.append((applicant, gap))
                print(f"  ❌ {applicant}: {gap:.1f}분 간격")
                print(f"     발표준비: {prep_data.iloc[0]['start_time']} ~ {prep_end}")
                print(f"     발표면접: {interview_start} ~ {interview_data.iloc[0]['end_time']}")
        
        success_rate = (success_count / len(applicants)) * 100 if len(applicants) > 0 else 0
        print(f"\n📊 **성공률**: {success_rate:.1f}% ({success_count}/{len(applicants)}명)")
        
        if success_rate == 100:
            print("🎉 **완벽한 연속배치 달성!**")
        elif success_rate >= 80:
            print("✅ **우수한 성과** - 대부분 연속배치 성공")
        elif success_rate >= 50:
            print("⚠️ **부분적 성공** - 추가 최적화 필요")
        else:
            print("❌ **개선 필요** - 근본적인 문제 존재")
        
        return success_rate
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return 0

def test_room_increase():
    """🎯 해결책 2: 발표준비실 개수 증가"""
    print("\n" + "="*60)
    print("=== 🎯 해결책 2: 발표준비실 개수 증가 ===")
    print("발표준비실을 2개로 늘려서 그룹 크기 축소")
    
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [2],  # 1개 → 2개로 증가
        "발표준비실_cap": [2],
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
        print(f"설정 변경사항:")
        print(f"- 발표준비실: 1개 → 2개")
        print(f"- 예상 그룹: 3개 → 2개 (3명씩)")
        
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
    print("=== 🎯 직접적인 해결책 비교 테스트 ===")
    print("디폴트 설정 변경 없이 알고리즘적으로 해결")
    
    # 해결책 1: individual 변환
    rate1 = test_direct_fix()
    
    # 해결책 2: 방 개수 증가
    rate2 = test_room_increase()
    
    print(f"\n=== 📊 최종 결과 ===")
    print(f"해결책 1 (individual 변환): {rate1:.1f}%")
    print(f"해결책 2 (방 개수 증가): {rate2:.1f}%")
    
    if max(rate1, rate2) >= 80:
        best = "해결책 1" if rate1 > rate2 else "해결책 2"
        print(f"🏆 **권장 해결책**: {best}")
        print("✅ 충분한 성능 달성!")
    else:
        print("❌ 추가 알고리즘 개선 필요")
        print("💡 고려사항: 스케줄러 내부 로직 수정 필요")

if __name__ == "__main__":
    main() 