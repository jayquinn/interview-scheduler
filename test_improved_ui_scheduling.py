#!/usr/bin/env python3
"""
UI 기본 규칙을 엄격히 적용한 개선된 스케줄링 테스트
사용자가 지적한 4가지 문제점을 해결하는 것이 목표:

1. 발표준비 → 발표면접 선후행 제약 100% 준수
2. 발표준비실 2명 동시 수용 능력 활용
3. 토론면접실 A, B 균등 활용
4. 방들의 동시간대 활용률 향상
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import os
import sys

# 필요한 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from solver.api import solve_for_days_v2
    from app import df_to_excel
    print("✅ 모듈 임포트 성공")
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

def create_improved_ui_config():
    """UI 기본 규칙을 엄격히 적용한 개선된 설정"""
    print("🔧 개선된 UI 설정 생성 중...")
    
    # 1. 활동 설정 - UI 기본값 + 최적화 파라미터
    activities = pd.DataFrame([
        {
            "activity": "토론면접",
            "mode": "batched",
            "duration_min": 30,
            "room_type": "토론면접실",
            "min_cap": 4,  # UI 기본값
            "max_cap": 6,  # UI 기본값
            "use": True
        },
        {
            "activity": "발표준비",
            "mode": "parallel",  # 이것이 핵심 - 2명이 동시에 할 수 있음
            "duration_min": 5,
            "room_type": "발표준비실",
            "min_cap": 1,
            "max_cap": 2,  # UI 기본값 - 2명 동시 수용
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
    
    # 2. 방 설정 - UI 기본값 엄격 적용
    room_plan = pd.DataFrame([{
        "토론면접실_count": 2,  # A, B 둘 다 사용
        "토론면접실_cap": 6,    # 각각 6명 수용
        "발표준비실_count": 1,  # 1개 방
        "발표준비실_cap": 2,    # 2명 동시 수용 가능
        "발표면접실_count": 2,  # A, B 둘 다 사용
        "발표면접실_cap": 1     # 각각 1명 수용
    }])
    
    # 3. 운영 시간 - UI 기본값
    oper_window = pd.DataFrame([{
        "start_time": "09:00",  # UI 기본값
        "end_time": "17:30"     # UI 기본값 (8.5시간)
    }])
    
    # 4. 선후행 제약 - UI 기본값 엄격 적용
    precedence = pd.DataFrame([{
        "predecessor": "발표준비",
        "successor": "발표면접", 
        "gap_min": 0,           # UI 기본값
        "adjacent": True        # 연속배치 필수
    }])
    
    # 5. 멀티데이트 계획 - 기존과 동일하지만 더 균등 분배
    today = datetime.now().date()
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
                {"code": "JOB05", "count": 11},
                {"code": "JOB06", "count": 11},
                {"code": "JOB07", "count": 11}
            ]
        },
        (today + timedelta(days=3)).strftime('%Y-%m-%d'): {
            "date": today + timedelta(days=3),
            "enabled": True,
            "jobs": [
                {"code": "JOB08", "count": 5},
                {"code": "JOB09", "count": 5},
                {"code": "JOB10", "count": 4},
                {"code": "JOB11", "count": 4}
            ]
        }
    }
    
    # 6. 직무별 활동 매핑 - 모든 직무가 모든 활동 수행
    job_acts_data = []
    for date_key, plan in multidate_plans.items():
        for job in plan["jobs"]:
            job_acts_data.append({
                "code": job["code"],
                "count": job["count"],
                "토론면접": True,
                "발표준비": True,
                "발표면접": True
            })
    
    job_acts_map = pd.DataFrame(job_acts_data)
    
    # 7. 최적화 파라미터
    interview_dates = [
        today,
        today + timedelta(days=1),
        today + timedelta(days=2),
        today + timedelta(days=3)
    ]
    
    return {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'multidate_plans': multidate_plans,
        'interview_dates': interview_dates,
        'group_min_size': 4,    # UI 기본값
        'group_max_size': 6,    # UI 기본값
        'global_gap_min': 5,    # UI 기본값
        'max_stay_hours': 4     # 체류시간 단축 목표
    }

def validate_improvements(df):
    """개선 사항 검증"""
    if df is None or df.empty:
        return "❌ 스케줄 데이터 없음"
    
    report = []
    report.append("🔍 개선 사항 검증 결과:")
    report.append("=" * 50)
    
    # 1. 선후행 제약 검증
    precedence_violations = 0
    continuity_violations = 0
    total_sequences = 0
    
    for applicant in df['applicant_id'].unique():
        applicant_schedule = df[df['applicant_id'] == applicant].sort_values('start_time')
        activities = applicant_schedule['activity_name'].tolist()
        
        if '발표준비' in activities and '발표면접' in activities:
            total_sequences += 1
            prep_idx = activities.index('발표준비')
            interview_idx = activities.index('발표면접')
            
            if prep_idx >= interview_idx:
                precedence_violations += 1
            else:
                # 연속성 체크
                prep_row = applicant_schedule.iloc[prep_idx]
                interview_row = applicant_schedule.iloc[interview_idx]
                
                prep_end = pd.to_datetime(f"{prep_row['interview_date']} {prep_row['end_time']}")
                interview_start = pd.to_datetime(f"{interview_row['interview_date']} {interview_row['start_time']}")
                
                gap_minutes = (interview_start - prep_end).total_seconds() / 60
                if gap_minutes > 10:  # 10분 초과면 연속성 문제
                    continuity_violations += 1
    
    precedence_success_rate = (total_sequences - precedence_violations) / total_sequences * 100 if total_sequences > 0 else 0
    report.append(f"1️⃣ 선후행 제약: {total_sequences - precedence_violations}/{total_sequences} ({precedence_success_rate:.1f}%)")
    
    if precedence_violations == 0:
        report.append("   ✅ 발표준비 → 발표면접 순서 100% 준수!")
    else:
        report.append(f"   ❌ 순서 위반 {precedence_violations}건")
    
    # 2. 발표준비실 2명 동시 수용 검증
    prep_schedules = df[df['activity_name'] == '발표준비'].copy()
    max_concurrent = 0
    concurrent_2_count = 0
    
    if not prep_schedules.empty:
        prep_schedules['datetime_start'] = pd.to_datetime(prep_schedules['interview_date'].astype(str) + ' ' + prep_schedules['start_time'].astype(str))
        prep_schedules['datetime_end'] = pd.to_datetime(prep_schedules['interview_date'].astype(str) + ' ' + prep_schedules['end_time'].astype(str))
        
        for idx, schedule in prep_schedules.iterrows():
            start = schedule['datetime_start']
            end = schedule['datetime_end']
            room = schedule['room_name']
            
            overlapping = prep_schedules[
                (prep_schedules['datetime_start'] < end) & 
                (prep_schedules['datetime_end'] > start) &
                (prep_schedules['room_name'] == room)
            ]
            
            concurrent_count = len(overlapping)
            max_concurrent = max(max_concurrent, concurrent_count)
            
            if concurrent_count == 2:
                concurrent_2_count += 1
    
    report.append(f"2️⃣ 발표준비실 동시 수용: 최대 {max_concurrent}명, 2명 동시 {concurrent_2_count//2}회")
    
    if max_concurrent >= 2:
        report.append("   ✅ 발표준비실 2명 수용 능력 활용됨!")
    else:
        report.append("   ❌ 발표준비실 2명 수용 능력 미활용")
    
    # 3. 토론면접실 A, B 균등 활용 검증
    discussion_rooms = df[df['activity_name'] == '토론면접']['room_name'].value_counts()
    room_balance = abs(discussion_rooms.max() - discussion_rooms.min()) if len(discussion_rooms) > 1 else 0
    
    report.append(f"3️⃣ 토론면접실 활용: {dict(discussion_rooms)}")
    
    if room_balance <= 5:  # 5회 이하 차이면 균등
        report.append("   ✅ 토론면접실 A, B 균등 활용됨!")
    else:
        report.append(f"   ❌ 토론면접실 불균등 (차이: {room_balance}회)")
    
    # 4. 방 활용률 계산
    room_usage = df.groupby(['room_name', 'activity_name']).size().reset_index(name='사용횟수')
    
    total_operating_hours = 8.5 * df['interview_date'].nunique()  # 8.5시간 * 일수
    
    prep_room_utilization = 0
    if '발표준비실' in df['room_name'].values:
        prep_duration_hours = df[df['room_name'].str.contains('발표준비실', na=False)]['duration_min'].sum() / 60
        prep_room_utilization = (prep_duration_hours / total_operating_hours) * 100
    
    report.append(f"4️⃣ 발표준비실 활용률: {prep_room_utilization:.1f}%")
    
    if prep_room_utilization > 60:  # 60% 이상이면 양호
        report.append("   ✅ 발표준비실 활용률 양호!")
    else:
        report.append("   ❌ 발표준비실 활용률 개선 필요")
    
    # 종합 점수
    score = 0
    if precedence_violations == 0:
        score += 25
    if max_concurrent >= 2:
        score += 25
    if room_balance <= 5:
        score += 25
    if prep_room_utilization > 60:
        score += 25
    
    report.append("")
    report.append(f"🎯 종합 점수: {score}/100점")
    
    if score >= 75:
        report.append("🎉 우수 - 대부분 문제 해결됨!")
    elif score >= 50:
        report.append("⚠️ 보통 - 일부 문제 해결됨")
    else:
        report.append("❌ 미흡 - 추가 개선 필요")
    
    return "\n".join(report)

def test_improved_ui_scheduling():
    """개선된 UI 스케줄링 테스트 실행"""
    print("🚀 개선된 UI 스케줄링 테스트 시작...")
    print("=" * 60)
    
    try:
        # 1. 개선된 설정 생성
        config = create_improved_ui_config()
        
        # 2. CP-SAT 솔버 파라미터 (실제 지원되는 파라미터만)
        params = {
            'time_limit_sec': 180.0,   # 3분으로 증가하여 더 나은 해 탐색
            'global_gap_min': 5,       # 활동 간 간격 (UI 기본값)
            'max_stay_hours': 4,       # 체류시간 단축 목표
            'group_min_size': 4,       # UI 기본값
            'group_max_size': 6        # UI 기본값
        }
        
        print(f"📋 설정 요약:")
        print(f"   - 총 지원자: {config['job_acts_map']['count'].sum()}명")
        print(f"   - 면접 일수: {len(config['interview_dates'])}일")
        print(f"   - 활동 수: {len(config['activities'])}개")
        print(f"   - 선후행 제약: {len(config['precedence'])}개")
        print(f"   - 시간 제한: {params['time_limit_sec']}초")
        
        # 3. 스케줄링 실행
        print(f"\n🔄 CP-SAT 스케줄링 실행 중...")
        result = solve_for_days_v2(config, params)
        
        if not result or len(result) < 2:
            print("❌ 스케줄링 결과 없음")
            return False, None, "스케줄링 실패"
        
        status = result[0]
        df = result[1] if len(result) > 1 else None
        
        # 4. 결과 분석
        if status in ['SUCCESS', 'FEASIBLE']:
            print(f"✅ 스케줄링 성공! (상태: {status})")
            
            if df is not None and not df.empty:
                print(f"📋 생성된 스케줄: {len(df)}개 활동, {df['applicant_id'].nunique()}명 지원자")
                
                # 5. 개선 사항 검증
                validation_report = validate_improvements(df)
                print(f"\n{validation_report}")
                
                # 6. Excel 파일 생성
                print("\n📥 Excel 파일 생성 중...")
                try:
                    excel_data = df_to_excel(df)
                    filename = f"improved_ui_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    
                    with open(filename, 'wb') as f:
                        f.write(excel_data.getvalue())
                    
                    print(f"✅ Excel 파일 저장 완료: {filename}")
                    print(f"📊 파일 크기: {len(excel_data.getvalue()):,} bytes")
                    
                    return True, filename, validation_report
                    
                except Exception as e:
                    print(f"❌ Excel 생성 실패: {e}")
                    return False, None, validation_report
            else:
                print("❌ 스케줄 데이터 없음")
                return False, None, "스케줄 데이터 없음"
        else:
            print(f"❌ 스케줄링 실패: {status}")
            return False, None, f"스케줄링 실패: {status}"
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, None, f"오류: {e}"

if __name__ == "__main__":
    success, filename, report = test_improved_ui_scheduling()
    
    if success:
        print(f"\n🎉 테스트 성공! 결과 파일: {filename}")
    else:
        print(f"\n❌ 테스트 실패: {report}") 