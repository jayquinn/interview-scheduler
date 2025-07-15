#!/usr/bin/env python3
"""
UI 엑셀 형식으로 결과 저장 테스트 (수정 버전)
UI 기본 설정을 정확히 반영하여 스케줄링 문제 해결
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from io import BytesIO
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

def create_correct_ui_defaults():
    """UI 기본 설정을 정확히 반영한 데이터 생성"""
    print("🔧 정확한 UI 기본 설정 데이터 생성 중...")
    
    # 1. 활동 설정 (app.py 기본값 정확히 반영)
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
            "min_cap": 1,  # UI 기본값: 1명
            "max_cap": 1,
            "use": True
        }
    ])
    
    # 2. 방 설정 (app.py 기본값 정확히 반영)
    room_plan = pd.DataFrame([{
        "토론면접실_count": 2,  # 토론면접실A, 토론면접실B
        "토론면접실_cap": 6,
        "발표준비실_count": 1,  # 발표준비실1 (2명 수용 가능)
        "발표준비실_cap": 2,
        "발표면접실_count": 2,  # 발표면접실A, 발표면접실B
        "발표면접실_cap": 1
    }])
    
    # 3. 운영 시간
    oper_window = pd.DataFrame([{
        "start_time": "09:00",
        "end_time": "17:30"
    }])
    
    # 4. 선후행 제약 (발표준비 → 발표면접)
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 5. 멀티데이트 계획 (4일, 137명)
    current_date = datetime.now().date()
    multidate_plans = {
        current_date.strftime('%Y-%m-%d'): {
            "date": current_date,
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 23},
                {"code": "JOB02", "count": 23}
            ]
        },
        (current_date + timedelta(days=1)).strftime('%Y-%m-%d'): {
            "date": current_date + timedelta(days=1),
            "enabled": True,
            "jobs": [
                {"code": "JOB03", "count": 20},
                {"code": "JOB04", "count": 20}
            ]
        },
        (current_date + timedelta(days=2)).strftime('%Y-%m-%d'): {
            "date": current_date + timedelta(days=2),
            "enabled": True,
            "jobs": [
                {"code": "JOB05", "count": 12},
                {"code": "JOB06", "count": 15},
                {"code": "JOB07", "count": 6}
            ]
        },
        (current_date + timedelta(days=3)).strftime('%Y-%m-%d'): {
            "date": current_date + timedelta(days=3),
            "enabled": True,
            "jobs": [
                {"code": "JOB08", "count": 6},
                {"code": "JOB09", "count": 6},
                {"code": "JOB10", "count": 3},
                {"code": "JOB11", "count": 3}
            ]
        }
    }
    
    # 6. 직무별 활동 매핑 (모든 직무가 3개 활동 모두 수행)
    job_acts_map_data = []
    for date_key, plan in multidate_plans.items():
        for job in plan.get("jobs", []):
            job_acts_map_data.append({
                "code": job["code"],
                "count": job["count"],
                "토론면접": True,
                "발표준비": True,
                "발표면접": True
            })
    
    job_acts_map = pd.DataFrame(job_acts_map_data)
    
    # 7. 면접 날짜 리스트
    interview_dates = list(multidate_plans.keys())
    
    # 8. 전역 설정
    global_config = {
        "group_min_size": 4,
        "group_max_size": 6,
        "global_gap_min": 5,
        "max_stay_hours": 5.0,
        "time_limit_sec": 300.0  # 5분 제한
    }
    
    print("✅ 정확한 UI 기본 설정 데이터 생성 완료")
    print(f"  - 활동: {len(activities)}개")
    print(f"  - 방: 토론면접실 {room_plan.iloc[0]['토론면접실_count']}개, 발표준비실 {room_plan.iloc[0]['발표준비실_count']}개, 발표면접실 {room_plan.iloc[0]['발표면접실_count']}개")
    print(f"  - 총 지원자: {job_acts_map['count'].sum()}명")
    print(f"  - 면접 날짜: {len(interview_dates)}일")
    print(f"  - 토론면접 그룹 크기: {activities[activities['activity']=='토론면접'].iloc[0]['min_cap']}~{activities[activities['activity']=='토론면접'].iloc[0]['max_cap']}명")
    print(f"  - 발표준비실 용량: 최대 {activities[activities['activity']=='발표준비'].iloc[0]['max_cap']}명")
    
    return {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'multidate_plans': multidate_plans,
        'interview_dates': interview_dates,
        **global_config
    }

def analyze_schedule_quality(df):
    """스케줄링 품질 분석"""
    if df is None or df.empty:
        return "스케줄 데이터 없음"
    
    analysis = []
    analysis.append(f"📊 스케줄링 품질 분석")
    analysis.append(f"=" * 50)
    
    # 1. 기본 통계
    total_applicants = df['applicant_id'].nunique()
    total_activities = len(df)
    analysis.append(f"총 지원자: {total_applicants}명")
    analysis.append(f"총 활동: {total_activities}개")
    
    # 2. 날짜별 분포
    analysis.append("\n📅 날짜별 분포:")
    date_stats = df.groupby('date').agg({
        'applicant_id': 'nunique',
        'activity': 'count'
    }).round(2)
    analysis.append(date_stats.to_string())
    
    # 3. 활동별 분포
    analysis.append("\n🎯 활동별 분포:")
    activity_stats = df.groupby('activity').agg({
        'applicant_id': 'nunique',
        'room': 'nunique'
    }).round(2)
    analysis.append(activity_stats.to_string())
    
    # 4. 방 활용률
    analysis.append("\n🏢 방 활용률:")
    room_stats = df.groupby(['room', 'activity']).size().reset_index(name='사용횟수')
    for _, row in room_stats.iterrows():
        analysis.append(f"  {row['room']} ({row['activity']}): {row['사용횟수']}회")
    
    # 5. 선후행 제약 검증
    analysis.append("\n🔗 선후행 제약 검증:")
    precedence_violations = 0
    for applicant in df['applicant_id'].unique():
        applicant_schedule = df[df['applicant_id'] == applicant].sort_values('start_time')
        activities = applicant_schedule['activity'].tolist()
        
        if '발표준비' in activities and '발표면접' in activities:
            prep_idx = activities.index('발표준비')
            interview_idx = activities.index('발표면접')
            if prep_idx >= interview_idx:
                precedence_violations += 1
    
    analysis.append(f"  선후행 제약 위반: {precedence_violations}건")
    
    # 6. 체류 시간 분석
    analysis.append("\n⏰ 체류 시간 분석:")
    stay_times = []
    for applicant in df['applicant_id'].unique():
        applicant_schedule = df[df['applicant_id'] == applicant].sort_values('start_time')
        if len(applicant_schedule) > 0:
            start = applicant_schedule.iloc[0]['start_time']
            end = applicant_schedule.iloc[-1]['end_time']
            stay_time = (end - start).total_seconds() / 3600
            stay_times.append(stay_time)
    
    if stay_times:
        analysis.append(f"  평균 체류시간: {np.mean(stay_times):.2f}시간")
        analysis.append(f"  최대 체류시간: {np.max(stay_times):.2f}시간")
        analysis.append(f"  최소 체류시간: {np.min(stay_times):.2f}시간")
    
    return "\n".join(analysis)

def test_correct_ui_scheduling():
    """정확한 UI 설정으로 스케줄링 테스트"""
    print("🚀 정확한 UI 설정으로 스케줄링 테스트 시작")
    print("=" * 60)
    
    try:
        # 1. 정확한 UI 기본 데이터 생성
        config = create_correct_ui_defaults()
        
        # 2. 스케줄링 실행
        print("\n🔄 CP-SAT 스케줄링 실행 중...")
        result = solve_for_days_v2(
            activities=config['activities'],
            job_acts_map=config['job_acts_map'],
            room_plan=config['room_plan'],
            oper_window=config['oper_window'],
            precedence=config['precedence'],
            multidate_plans=config['multidate_plans'],
            interview_dates=config['interview_dates'],
            params={
                'time_limit_sec': config['time_limit_sec'],
                'group_min_size': config['group_min_size'],
                'group_max_size': config['group_max_size'],
                'global_gap_min': config['global_gap_min'],
                'max_stay_hours': config['max_stay_hours']
            }
        )
        
        # 3. 결과 분석
        if result and result.get('status') == 'FEASIBLE':
            print(f"✅ 스케줄링 성공! (상태: {result['status']})")
            
            df = result.get('schedule_df')
            if df is not None and not df.empty:
                print(f"📋 생성된 스케줄: {len(df)}개 활동, {df['applicant_id'].nunique()}명 지원자")
                
                # 4. 품질 분석
                quality_report = analyze_schedule_quality(df)
                print(f"\n{quality_report}")
                
                # 5. Excel 파일 생성
                print("\n📥 Excel 파일 생성 중...")
                try:
                    excel_data = df_to_excel(df)
                    
                    # 파일 저장
                    filename = f"fixed_ui_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    with open(filename, 'wb') as f:
                        f.write(excel_data.getvalue())
                    
                    print(f"✅ Excel 파일 저장 완료: {filename}")
                    print(f"📊 파일 크기: {len(excel_data.getvalue()):,} bytes")
                    
                    return True, filename, quality_report
                    
                except Exception as e:
                    print(f"❌ Excel 생성 실패: {e}")
                    return False, None, quality_report
            else:
                print("❌ 스케줄 데이터 없음")
                return False, None, "스케줄 데이터 없음"
        else:
            print(f"❌ 스케줄링 실패: {result.get('status', 'UNKNOWN') if result else 'No result'}")
            return False, None, "스케줄링 실패"
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, None, f"오류: {e}"

def main():
    """메인 실행 함수"""
    print("🎯 UI 기본 설정 정확 반영 테스트")
    print("=" * 60)
    
    success, filename, report = test_correct_ui_scheduling()
    
    if success:
        print(f"\n🎉 테스트 성공!")
        print(f"📁 파일: {filename}")
        print(f"📊 품질 리포트:")
        print(report)
    else:
        print(f"\n💥 테스트 실패")
        if report:
            print(f"📄 리포트: {report}")

if __name__ == "__main__":
    main() 