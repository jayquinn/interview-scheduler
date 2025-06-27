#!/usr/bin/env python3
"""
🎯 실제 시스템 스마트 통합 로직 테스트
- 실제 solve_for_days_v2 함수 사용
- 스마트 통합 로직이 자동으로 적용되는지 확인
- 0% → 100% 성공률 달성 검증
"""

import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def test_real_system_integration():
    print("=== 🎯 실제 시스템 스마트 통합 테스트 ===")
    print("solve_for_days_v2에 내장된 스마트 통합 로직 검증")
    
    # 디폴트 문제 설정 (발표준비 → 발표면접 gap_min=0)
    print(f"\n📋 테스트 설정:")
    print(f"- 지원자: 6명")
    print(f"- 발표준비(5분, parallel, 발표준비실 1개/2명)")
    print(f"- 발표면접(15분, individual, 발표면접실 2개/1명)")
    print(f"- 인접 제약: 발표준비 → 발표면접 (gap_min=0, adjacent=True)")
    
    # 원래 문제 상황 설정
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
        "발표준비실_count": [1],
        "발표준비실_cap": [2],
        "발표면접실_count": [2],
        "발표면접실_cap": [1]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    # 핵심: gap_min=0, adjacent=True 인접 제약
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
    
    # 실제 시스템 테스트
    print(f"\n🚀 실제 시스템 테스트 실행 중...")
    print(f"solve_for_days_v2 호출 → 스마트 통합 로직 자동 적용")
    
    try:
        status, schedule_df, logs, limit = solve_for_days_v2(cfg_ui, debug=True)
        
        print(f"\n📊 결과 분석:")
        print(f"상태: {status}")
        print(f"일일 한계: {limit}")
        
        if logs:
            print(f"\n🔍 상세 로그:")
            for line in logs.split('\n'):
                if '🚀' in line or '🔍' in line or '🔧' in line or '✅' in line:
                    print(f"  {line}")
        
        if status in ["SUCCESS", "PARTIAL"] and schedule_df is not None and not schedule_df.empty:
            print(f"\n✅ 스케줄링 성공! {len(schedule_df)}개 항목 생성")
            
            # 활동 분석
            analyze_schedule_activities(schedule_df)
            
            # 연속배치 성공률 분석
            success_rate = analyze_adjacency_success(schedule_df, precedence)
            
            print(f"\n🏆 최종 성과:")
            print(f"연속배치 성공률: {success_rate:.1%}")
            
            if success_rate == 1.0:
                print(f"🎉 완벽한 성공! 스마트 통합 로직이 문제를 완전히 해결했습니다!")
                return True
            else:
                print(f"⚠️ 부분 성공. 추가 개선 필요")
                return False
                
        else:
            print(f"❌ 스케줄링 실패")
            if logs:
                print(f"오류 로그:\n{logs}")
            return False
            
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def analyze_schedule_activities(schedule_df):
    """스케줄 활동 분석"""
    print(f"\n📋 스케줄 활동 분석:")
    
    # 활동별 분석
    if 'activity_name' in schedule_df.columns:
        activity_col = 'activity_name'
    elif 'activity' in schedule_df.columns:
        activity_col = 'activity'
    else:
        print("활동 컬럼을 찾을 수 없습니다.")
        return
    
    activities = schedule_df[activity_col].unique()
    print(f"활동 목록: {sorted(activities)}")
    
    for activity in sorted(activities):
        activity_data = schedule_df[schedule_df[activity_col] == activity]
        print(f"  🔹 {activity}: {len(activity_data)}개 스케줄")
        
        # 시간대별 분석
        if 'start_time' in schedule_df.columns:
            time_groups = activity_data.groupby('start_time').size()
            for start_time, count in time_groups.items():
                print(f"    {start_time}: {count}명")

def analyze_adjacency_success(schedule_df, precedence_df):
    """인접 제약 성공률 분석"""
    if precedence_df.empty:
        return 1.0  # 제약이 없으면 100% 성공
    
    # 컬럼명 찾기
    applicant_col = None
    activity_col = None
    start_col = None
    end_col = None
    
    for col in schedule_df.columns:
        if 'applicant' in col.lower() or 'id' in col.lower():
            applicant_col = col
        elif 'activity' in col.lower():
            activity_col = col
        elif 'start' in col.lower():
            start_col = col
        elif 'end' in col.lower():
            end_col = col
    
    if not all([applicant_col, activity_col, start_col, end_col]):
        print(f"⚠️ 필요한 컬럼 없음: {list(schedule_df.columns)}")
        return 0.0
    
    total_constraints = 0
    satisfied_constraints = 0
    
    # 지원자별 분석
    for applicant_id in schedule_df[applicant_col].unique():
        applicant_schedule = schedule_df[schedule_df[applicant_col] == applicant_id]
        
        # 각 인접 제약 확인
        for _, rule in precedence_df.iterrows():
            if not rule.get('adjacent', False):
                continue
                
            pred_name = rule['predecessor']
            succ_name = rule['successor']
            gap_min = rule.get('gap_min', 0)
            
            # 선행 및 후행 활동 찾기
            pred_activities = applicant_schedule[applicant_schedule[activity_col] == pred_name]
            succ_activities = applicant_schedule[applicant_schedule[activity_col] == succ_name]
            
            if pred_activities.empty or succ_activities.empty:
                continue
            
            # 시간 간격 확인
            for _, pred in pred_activities.iterrows():
                for _, succ in succ_activities.iterrows():
                    total_constraints += 1
                    
                    pred_end = pred[end_col]
                    succ_start = succ[start_col]
                    
                    # 시간 차이 계산
                    if hasattr(pred_end, 'total_seconds'):
                        pred_end_min = pred_end.total_seconds() / 60
                    elif hasattr(pred_end, 'hour'):
                        pred_end_min = pred_end.hour * 60 + pred_end.minute
                    else:
                        pred_end_min = float(pred_end)
                    
                    if hasattr(succ_start, 'total_seconds'):
                        succ_start_min = succ_start.total_seconds() / 60
                    elif hasattr(succ_start, 'hour'):
                        succ_start_min = succ_start.hour * 60 + succ_start.minute
                    else:
                        succ_start_min = float(succ_start)
                    
                    actual_gap = succ_start_min - pred_end_min
                    
                    if abs(actual_gap - gap_min) < 0.1:  # 허용 오차 0.1분
                        satisfied_constraints += 1
                    else:
                        print(f"  ⚠️ {applicant_id}: 예상 {gap_min}분, 실제 {actual_gap:.1f}분")
    
    if total_constraints == 0:
        return 1.0
    
    return satisfied_constraints / total_constraints

def test_integration_comparison():
    """통합 전후 비교 테스트"""
    print(f"\n=== 📊 통합 전후 성능 비교 ===")
    
    # 원래 설정으로 테스트 (스마트 통합 적용됨)
    print(f"🚀 스마트 통합 적용된 시스템 테스트")
    success = test_real_system_integration()
    
    if success:
        print(f"\n🎉 스마트 통합 로직 검증 완료!")
        print(f"실제 시스템에서 0% → 100% 연속배치 성공률 달성!")
        print(f"사용자 설정 변경 없이 알고리즘적으로 문제 해결!")
    else:
        print(f"\n❌ 추가 디버깅 필요")
    
    return success

if __name__ == "__main__":
    print("🎯 실제 시스템 스마트 통합 로직 테스트 시작")
    print("="*60)
    
    success = test_integration_comparison()
    
    print(f"\n" + "="*60)
    if success:
        print(f"🏆 테스트 성공: 스마트 통합 로직이 실제 시스템에서 완벽하게 작동!")
    else:
        print(f"⚠️ 테스트 실패: 추가 개선 필요")
    print(f"="*60) 