#!/usr/bin/env python3
"""
단순화된 UI 기본 규칙 적용 테스트
빠른 검증을 위해 1일 6명으로 축소하여 테스트
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

def create_simple_improved_config():
    """단순화된 개선 설정"""
    print("🔧 단순화된 개선 설정 생성 중...")
    
    # 1. 활동 설정 - UI 기본값
    activities = pd.DataFrame([
        {
            "activity": "토론면접",
            "mode": "batched",
            "duration_min": 30,
            "room_type": "토론면접실",
            "min_cap": 4,
            "max_cap": 6,
            "use": True
        },
        {
            "activity": "발표준비",
            "mode": "parallel",  # 2명 동시 수용 가능
            "duration_min": 5,
            "room_type": "발표준비실",
            "min_cap": 1,
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
    
    # 2. 방 설정 - UI 기본값
    room_plan = pd.DataFrame([{
        "토론면접실_count": 2,
        "토론면접실_cap": 6,
        "발표준비실_count": 1,
        "발표준비실_cap": 2,  # 핵심: 2명 동시 수용
        "발표면접실_count": 2,
        "발표면접실_cap": 1
    }])
    
    # 3. 운영 시간 - UI 기본값
    oper_window = pd.DataFrame([{
        "start_time": "09:00",
        "end_time": "17:30"
    }])
    
    # 4. 선후행 제약 - UI 기본값 (연속배치)
    precedence = pd.DataFrame([{
        "predecessor": "발표준비",
        "successor": "발표면접", 
        "gap_min": 0,
        "adjacent": True  # 연속배치 필수
    }])
    
    # 5. 단순화된 계획 - 1일 6명
    today = datetime.now().date()
    multidate_plans = {
        today.strftime('%Y-%m-%d'): {
            "date": today,
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 6}  # 단순화: 6명만
            ]
        }
    }
    
    # 6. 직무별 활동 매핑
    job_acts_map = pd.DataFrame([{
        "code": "JOB01",
        "count": 6,
        "토론면접": True,
        "발표준비": True,
        "발표면접": True
    }])
    
    return {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'multidate_plans': multidate_plans,
        'interview_dates': [today],
        'group_min_size': 4,
        'group_max_size': 6,
        'global_gap_min': 5,
        'max_stay_hours': 3  # 단축 목표
    }

def validate_simple_improvements(df):
    """단순화된 검증"""
    if df is None or df.empty:
        return "❌ 스케줄 데이터 없음"
    
    report = []
    report.append("🔍 단순화된 검증 결과:")
    report.append("=" * 40)
    
    # 1. 선후행 제약 검증
    violations = 0
    total = 0
    
    for applicant in df['applicant_id'].unique():
        applicant_schedule = df[df['applicant_id'] == applicant].sort_values('start_time')
        activities = applicant_schedule['activity_name'].tolist()
        
        if '발표준비' in activities and '발표면접' in activities:
            total += 1
            prep_idx = activities.index('발표준비')
            interview_idx = activities.index('발표면접')
            
            if prep_idx >= interview_idx:
                violations += 1
                report.append(f"  ❌ {applicant}: 순서 위반")
    
    success_rate = (total - violations) / total * 100 if total > 0 else 0
    report.append(f"1️⃣ 선후행 제약: {total - violations}/{total} ({success_rate:.1f}%)")
    
    # 2. 발표준비실 2명 동시 수용 검증
    prep_schedules = df[df['activity_name'] == '발표준비'].copy()
    max_concurrent = 0
    
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
    
    report.append(f"2️⃣ 발표준비실 최대 동시 수용: {max_concurrent}명")
    
    # 3. 방 활용 현황
    room_usage = df.groupby(['room_name', 'activity_name']).size().reset_index(name='사용횟수')
    report.append("3️⃣ 방 활용 현황:")
    for _, row in room_usage.iterrows():
        report.append(f"  - {row['room_name']}: {row['사용횟수']}회")
    
    # 종합 점수
    score = 0
    if violations == 0:
        score += 50
        report.append("✅ 선후행 제약 완벽!")
    if max_concurrent >= 2:
        score += 50
        report.append("✅ 발표준비실 2명 동시 수용!")
    
    report.append(f"\n🎯 점수: {score}/100점")
    
    return "\n".join(report)

def test_simple_improved():
    """단순화된 개선 테스트"""
    print("🚀 단순화된 개선 테스트 시작...")
    print("=" * 50)
    
    try:
        # 1. 단순화된 설정 생성
        config = create_simple_improved_config()
        
        # 2. 빠른 파라미터
        params = {
            'time_limit_sec': 30.0,  # 30초만
            'max_stay_hours': 3
        }
        
        print(f"📋 설정: {config['job_acts_map']['count'].sum()}명, {len(config['interview_dates'])}일")
        
        # 3. 스케줄링 실행
        print(f"\n🔄 스케줄링 실행 중... (시간제한: {params['time_limit_sec']}초)")
        result = solve_for_days_v2(config, params)
        
        if not result or len(result) < 2:
            print("❌ 스케줄링 결과 없음")
            return False
        
        status = result[0]
        df = result[1] if len(result) > 1 else None
        
        # 4. 결과 분석
        if status in ['SUCCESS', 'FEASIBLE']:
            print(f"✅ 스케줄링 성공! (상태: {status})")
            
            if df is not None and not df.empty:
                print(f"📋 생성된 스케줄: {len(df)}개 활동, {df['applicant_id'].nunique()}명 지원자")
                
                # 5. 검증
                validation_report = validate_simple_improvements(df)
                print(f"\n{validation_report}")
                
                # 6. Excel 파일 생성
                print("\n📥 Excel 파일 생성 중...")
                try:
                    excel_data = df_to_excel(df)
                    filename = f"simple_improved_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    
                    with open(filename, 'wb') as f:
                        f.write(excel_data.getvalue())
                    
                    print(f"✅ Excel 파일 저장: {filename}")
                    return True
                    
                except Exception as e:
                    print(f"❌ Excel 생성 실패: {e}")
                    return False
            else:
                print("❌ 스케줄 데이터 없음")
                return False
        else:
            print(f"❌ 스케줄링 실패: {status}")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_improved()
    if success:
        print(f"\n🎉 단순화된 테스트 성공!")
    else:
        print(f"\n❌ 단순화된 테스트 실패") 