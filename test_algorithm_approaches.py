import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2
import json

def create_base_config():
    """기본 디폴트 설정"""
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
    
    return {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }

def analyze_results(result, test_name):
    """결과 분석"""
    print(f"\n=== {test_name} ===")
    
    # solve_for_days_v2는 (status, df, logs, limit) 튜플을 반환
    if isinstance(result, tuple) and len(result) >= 2:
        status, schedule, logs, limit = result
    else:
        print("❌ 잘못된 결과 형식")
        return None
    
    if status not in ["SUCCESS", "PARTIAL"]:
        print(f"❌ 스케줄링 실패 (상태: {status})")
        if logs:
            print(f"로그: {logs}")
        return None
    
    if schedule is None or schedule.empty:
        print("❌ 빈 스케줄")
        return None
    
    print(f"✅ 스케줄링 성공 ({len(schedule)}개 항목)")
    
    # 선후행 제약 분석
    violations = []
    success_count = 0
    
    # 컬럼 이름 확인
    applicant_col = None
    activity_col = None
    start_col = None
    end_col = None
    
    for col in schedule.columns:
        if 'applicant' in col.lower() or 'id' in col.lower():
            applicant_col = col
        elif 'activity' in col.lower():
            activity_col = col
        elif 'start' in col.lower():
            start_col = col
        elif 'end' in col.lower():
            end_col = col
    
    if not all([applicant_col, activity_col, start_col, end_col]):
        print(f"❌ 필요한 컬럼 없음: {list(schedule.columns)}")
        return None
    
    # 지원자별로 발표준비 → 발표면접 간격 확인
    applicants = schedule[applicant_col].unique()
    
    for applicant in applicants:
        app_schedule = schedule[schedule[applicant_col] == applicant].copy()
        
        prep_rows = app_schedule[app_schedule[activity_col] == '발표준비']
        present_rows = app_schedule[app_schedule[activity_col] == '발표면접']
        
        if prep_rows.empty or present_rows.empty:
            continue
            
        prep_end = pd.to_datetime(prep_rows.iloc[0][end_col])
        present_start = pd.to_datetime(present_rows.iloc[0][start_col])
        
        gap_minutes = (present_start - prep_end).total_seconds() / 60
        
        if gap_minutes == 0:  # 연속배치 성공
            success_count += 1
            print(f"  ✅ {applicant}: 0분 간격 (연속배치)")
        else:
            violations.append((applicant, gap_minutes))
            print(f"  ❌ {applicant}: {gap_minutes}분 간격")
    
    success_rate = (success_count / len(applicants)) * 100 if applicants.size > 0 else 0
    print(f"📊 성공률: {success_rate:.1f}% ({success_count}/{len(applicants)}명)")
    
    return {
        'success_count': success_count,
        'total_count': len(applicants),
        'success_rate': success_rate,
        'violations': violations
    }

def test_current_approach():
    """현재 접근법 테스트"""
    cfg = create_base_config()
    
    try:
        result = solve_for_days_v2(cfg)
        return analyze_results(result, "현재 접근법 (디폴트)")
    except Exception as e:
        print(f"❌ 현재 접근법 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("=== 🧠 알고리즘적 접근 방법 분석 ===")
    print("디폴트 설정으로 다양한 해결책 검토")
    print(f"설정: 토론면접실 2개, 발표준비실 1개(2명), 발표면접실 2개")
    print(f"제약: 발표준비 → 발표면접 (연속배치, 0분 간격)")
    print(f"테스트 인원: 6명")
    
    # 1. 현재 접근법 테스트
    current_result = test_current_approach()
    
    print("\n" + "="*60)
    print("🤔 문제 분석 및 해결 아이디어")
    print("="*60)
    
    print("\n📋 현재 문제점:")
    print("1. 발표준비(parallel) → 3개 그룹 (2명, 2명, 2명)")
    print("2. 발표면접실 2개 → 동시에 2명만 처리 가능")
    print("3. 첫 그룹 이후 대기 시간 발생")
    
    print("\n💡 해결 아이디어들:")
    print("1. 🔗 인접 제약 묶음 처리: 발표준비+발표면접을 하나의 블록으로 처리")
    print("2. 🎯 역방향 스케줄링: 발표면접부터 역산해서 발표준비 배치")
    print("3. 📊 그룹 크기 최적화: 발표준비 그룹을 발표면접실 수에 맞춤")
    print("4. ⏰ 타임슬롯 예약: 발표면접 시간을 먼저 예약하고 발표준비 배치")
    print("5. 🔄 순서 변경: individual 먼저, parallel 나중에")
    
    print("\n🎯 가장 유망한 접근법:")
    print("**인접 제약 묶음 처리**: 발표준비+발표면접을 atomic 블록으로 처리")
    print("- 발표준비 5분 + 발표면접 15분 = 20분 블록")
    print("- 이 블록을 개별 지원자에게 할당")
    print("- 발표준비실과 발표면접실을 연계해서 스케줄링")
    
    if current_result:
        print(f"\n📊 현재 성능: {current_result['success_rate']:.1f}%")
        print("목표: 알고리즘 개선으로 100% 달성")

if __name__ == "__main__":
    main() 