#!/usr/bin/env python3
"""
사용자 지적 문제점 빠른 검증 테스트
- 발표준비 -> 발표면접 선후행 제약 검증
- 방 활용률 검증 
- 토론면접실 A, B 모두 사용 검증
- 발표준비실 2명 수용 검증
"""

import pandas as pd
from datetime import datetime, timedelta, time
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from solver.api import solve_for_days_v2
    from app import df_to_excel
    print("✅ 모듈 임포트 성공")
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

def create_simple_test_data():
    """간단한 테스트 데이터 생성 (24명, 1일)"""
    print("🔧 간단한 테스트 데이터 생성 중...")
    
    # 1. 활동 설정 (UI 기본값 정확히 반영)
    activities = pd.DataFrame([
        {
            "activity": "토론면접",
            "mode": "batched",
            "duration_min": 30,
            "room_type": "토론면접실",
            "min_cap": 4,  # UI 기본값: 4~6명
            "max_cap": 6,
            "use": True
        },
        {
            "activity": "발표준비",
            "mode": "parallel",
            "duration_min": 5,
            "room_type": "발표준비실",
            "min_cap": 1,  # UI 기본값: 1~2명
            "max_cap": 2,
            "use": True
        },
        {
            "activity": "발표면접",
            "mode": "individual",
            "duration_min": 15,
            "room_type": "발표면접실",
            "min_cap": 1,
            "max_cap": 1,
            "use": True
        }
    ])
    
    # 2. 방 설정 (UI 기본값)
    room_plan = pd.DataFrame([{
        "토론면접실_count": 2,  # 토론면접실A, 토론면접실B
        "토론면접실_cap": 6,
        "발표준비실_count": 1,  # 발표준비실1 (2명 수용)
        "발표준비실_cap": 2,
        "발표면접실_count": 2,  # 발표면접실A, 발표면접실B
        "발표면접실_cap": 1
    }])
    
    # 3. 운영 시간
    oper_window = pd.DataFrame([{
        "start_time": "09:00",
        "end_time": "17:30"
    }])
    
    # 4. 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 5. 하루 계획 (24명)
    current_date = datetime.now().date()
    multidate_plans = {
        current_date.strftime('%Y-%m-%d'): {
            "date": current_date,
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 24}  # 24명으로 간단히
            ]
        }
    }
    
    # 6. 직무별 활동 매핑
    job_acts_map = pd.DataFrame([{
        "code": "JOB01",
        "count": 24,
        "토론면접": True,
        "발표준비": True,
        "발표면접": True
    }])
    
    interview_dates = [current_date.strftime('%Y-%m-%d')]
    
    return {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'multidate_plans': multidate_plans,
        'interview_dates': interview_dates,
        'time_limit_sec': 60.0,  # 1분 제한
        'group_min_size': 4,
        'group_max_size': 6,
        'global_gap_min': 5,
        'max_stay_hours': 5.0
    }

def validate_user_issues(df):
    """사용자가 지적한 문제점들 검증"""
    if df is None or df.empty:
        return "❌ 스케줄 데이터 없음"
    
    issues = []
    issues.append("🔍 사용자 지적 문제점 검증")
    issues.append("=" * 50)
    
    # 1. 발표준비 → 발표면접 선후행 제약 검증
    issues.append("\n1️⃣ 발표준비 → 발표면접 선후행 제약 검증:")
    precedence_violations = 0
    valid_sequences = 0
    
    for applicant in df['applicant_id'].unique():
        applicant_schedule = df[df['applicant_id'] == applicant].sort_values('start_time')
        activities = applicant_schedule['activity'].tolist()
        
        if '발표준비' in activities and '발표면접' in activities:
            prep_idx = activities.index('발표준비')
            interview_idx = activities.index('발표면접')
            
            if prep_idx >= interview_idx:
                precedence_violations += 1
                issues.append(f"  ❌ {applicant}: 순서 위반 (발표준비 {prep_idx} >= 발표면접 {interview_idx})")
            else:
                valid_sequences += 1
                
                # 연속성 체크 (adjacent=True)
                prep_end = applicant_schedule.iloc[prep_idx]['end_time']
                interview_start = applicant_schedule.iloc[interview_idx]['start_time']
                gap = (interview_start - prep_end).total_seconds() / 60
                
                if gap > 5:  # 5분 초과 간격이면 연속성 위반
                    issues.append(f"  ⚠️ {applicant}: 연속성 위반 (간격 {gap}분)")
                else:
                    issues.append(f"  ✅ {applicant}: 올바른 순서 및 연속성 (간격 {gap}분)")
    
    issues.append(f"  📊 결과: 올바른 순서 {valid_sequences}건, 위반 {precedence_violations}건")
    
    # 2. 방 활용률 검증
    issues.append("\n2️⃣ 방 활용률 검증:")
    room_usage = df.groupby(['room', 'activity']).size().reset_index(name='사용횟수')
    
    for _, row in room_usage.iterrows():
        issues.append(f"  {row['room']} ({row['activity']}): {row['사용횟수']}회")
    
    # 토론면접실 A, B 모두 사용되는지 확인
    discussion_rooms = room_usage[room_usage['activity'] == '토론면접']['room'].tolist()
    if '토론면접실A' in discussion_rooms and '토론면접실B' in discussion_rooms:
        issues.append("  ✅ 토론면접실A, B 모두 활용됨")
    else:
        issues.append("  ❌ 토론면접실 중 일부만 사용됨")
    
    # 3. 발표준비실 동시 수용 검증
    issues.append("\n3️⃣ 발표준비실 동시 수용 검증:")
    prep_schedules = df[df['activity'] == '발표준비'].copy()
    
    if not prep_schedules.empty:
        # 시간대별 동시 사용자 수 계산
        max_concurrent = 0
        total_concurrent_2 = 0  # 2명 동시 사용한 경우
        
        for _, schedule in prep_schedules.iterrows():
            start = schedule['start_time']
            end = schedule['end_time']
            
            # 같은 시간대에 겹치는 다른 발표준비 일정 찾기
            overlapping = prep_schedules[
                (prep_schedules['start_time'] < end) & 
                (prep_schedules['end_time'] > start) &
                (prep_schedules['room'] == schedule['room'])
            ]
            
            concurrent_count = len(overlapping)
            max_concurrent = max(max_concurrent, concurrent_count)
            
            if concurrent_count == 2:
                total_concurrent_2 += 1
        
        issues.append(f"  최대 동시 사용자: {max_concurrent}명")
        issues.append(f"  2명 동시 사용 횟수: {total_concurrent_2//2}회")  # 중복 제거
        
        if max_concurrent == 2:
            issues.append("  ✅ 발표준비실 2명 수용 능력 활용됨")
        else:
            issues.append("  ❌ 발표준비실 2명 수용 능력 미활용")
    
    # 4. 전체 시간 활용률
    issues.append("\n4️⃣ 전체 시간 활용률:")
    
    # 운영 시간 대비 각 방의 사용률
    operating_hours = 8.5  # 09:00 ~ 17:30
    
    for room_type in ['토론면접실', '발표준비실', '발표면접실']:
        room_schedules = df[df['room'].str.contains(room_type)]
        if not room_schedules.empty:
            total_minutes = room_schedules['duration_min'].sum()
            utilization = (total_minutes / 60) / operating_hours * 100
            issues.append(f"  {room_type} 활용률: {utilization:.1f}%")
    
    return "\n".join(issues)

def test_simple_ui_fix():
    """간단한 UI 수정 테스트"""
    print("🚀 간단한 UI 문제점 수정 테스트")
    print("=" * 50)
    
    try:
        # 1. 테스트 데이터 생성
        config = create_simple_test_data()
        
        # 2. 스케줄링 실행
        print("\n🔄 CP-SAT 스케줄링 실행 중 (24명, 1일)...")
        
        # cfg_ui 형식으로 변환
        cfg_ui = {
            'activities': config['activities'],
            'job_acts_map': config['job_acts_map'], 
            'room_plan': config['room_plan'],
            'oper_window': config['oper_window'],
            'precedence': config['precedence'],
            'multidate_plans': config['multidate_plans'],
            'interview_dates': config['interview_dates']
        }
        
        params = {
            'time_limit_sec': config['time_limit_sec'],
            'group_min_size': config['group_min_size'],
            'group_max_size': config['group_max_size'],
            'global_gap_min': config['global_gap_min'],
            'max_stay_hours': config['max_stay_hours']
        }
        
        status, df, log_msg, daily_limit = solve_for_days_v2(cfg_ui, params)
        
        # 3. 결과 검증
        if status in ['SUCCESS', 'PARTIAL']:
            print(f"✅ 스케줄링 성공! (상태: {status})")
            
            if df is not None and not df.empty:
                print(f"📋 생성된 스케줄: {len(df)}개 활동, {df['applicant_id'].nunique()}명 지원자")
                
                # 4. 문제점 검증
                validation_report = validate_user_issues(df)
                print(f"\n{validation_report}")
                
                # 5. Excel 파일 생성
                print("\n📥 Excel 파일 생성 중...")
                try:
                    excel_data = df_to_excel(df)
                    filename = f"simple_ui_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    
                    with open(filename, 'wb') as f:
                        f.write(excel_data.getvalue())
                    
                    print(f"✅ Excel 파일 저장 완료: {filename}")
                    return True, filename, validation_report
                    
                except Exception as e:
                    print(f"❌ Excel 생성 실패: {e}")
                    return False, None, validation_report
            else:
                print("❌ 스케줄 데이터 없음")
                return False, None, "스케줄 데이터 없음"
        else:
            print(f"❌ 스케줄링 실패: {status}")
            print(f"로그: {log_msg}")
            return False, None, f"스케줄링 실패: {status}"
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, None, f"오류: {e}"

if __name__ == "__main__":
    success, filename, report = test_simple_ui_fix()
    
    if success:
        print(f"\n🎉 테스트 성공!")
        print(f"📁 파일: {filename}")
    else:
        print(f"\n💥 테스트 실패")
        if report:
            print(f"📄 리포트: {report}") 