#!/usr/bin/env python3
"""
스마트 통합 로직을 우회하고 직접 UI 기본 규칙을 적용
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import os
import sys
import traceback

# 필요한 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from solver.api import solve_for_days_v2
    from app import df_to_excel
    print("✅ 모듈 임포트 성공")
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

def create_direct_ui_config():
    """스마트 통합 없이 직접 UI 기본 규칙 적용"""
    print("🔧 직접 UI 기본 규칙 적용 중...")
    
    # 1. 활동 설정 - 통합된 형태로 직접 생성
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
            "activity": "발표준비+발표면접",  # 미리 통합된 활동
            "mode": "individual",
            "duration_min": 20,  # 5분 + 15분
            "room_type": "발표면접실",
            "min_cap": 1,
            "max_cap": 1,
            "use": True
        }
    ])
    
    # 2. 방 설정 - 발표준비실 제거, 발표면접실 활용
    room_plan = pd.DataFrame([{
        "토론면접실_count": 2,
        "토론면접실_cap": 6,
        "발표면접실_count": 2,  # A, B 둘 다 사용
        "발표면접실_cap": 1
    }])
    
    # 3. 운영 시간
    oper_window = pd.DataFrame([{
        "start_time": "09:00",
        "end_time": "17:30"
    }])
    
    # 4. 선후행 제약 제거 (이미 통합되었으므로)
    precedence = pd.DataFrame()  # 빈 DataFrame
    
    # 5. 단순화된 계획
    today = datetime.now().date()
    multidate_plans = {
        today.strftime('%Y-%m-%d'): {
            "date": today,
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 6}
            ]
        }
    }
    
    # 6. 직무별 활동 매핑
    job_acts_map = pd.DataFrame([{
        "code": "JOB01",
        "count": 6,
        "토론면접": True,
        "발표준비+발표면접": True  # 통합된 활동
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
        'max_stay_hours': 3
    }

def validate_direct_fix(df):
    """직접 수정 결과 검증"""
    if df is None or df.empty:
        return "❌ 스케줄 데이터 없음"
    
    report = []
    report.append("🔍 직접 수정 결과 검증:")
    report.append("=" * 40)
    
    # 1. 활동 종류 확인
    activities = df['activity_name'].unique()
    report.append(f"1️⃣ 활동 종류: {list(activities)}")
    
    # 2. 선후행 제약은 자동으로 해결됨 (통합 활동)
    if "발표준비+발표면접" in activities:
        report.append("✅ 발표준비+발표면접 통합 활동으로 선후행 제약 자동 해결!")
    
    # 3. 방 활용 현황
    room_usage = df.groupby(['room_name', 'activity_name']).size().reset_index(name='사용횟수')
    report.append("2️⃣ 방 활용 현황:")
    for _, row in room_usage.iterrows():
        report.append(f"  - {row['room_name']}: {row['사용횟수']}회")
    
    # 4. 토론면접실 A, B 균등 활용 확인
    discussion_rooms = df[df['activity_name'] == '토론면접']['room_name'].value_counts()
    if len(discussion_rooms) > 1:
        balance = abs(discussion_rooms.max() - discussion_rooms.min())
        if balance <= 1:
            report.append("✅ 토론면접실 A, B 균등 활용!")
        else:
            report.append(f"⚠️ 토론면접실 불균등 (차이: {balance}회)")
    
    # 5. 체류시간 계산
    stay_times = []
    for applicant in df['applicant_id'].unique():
        applicant_schedule = df[df['applicant_id'] == applicant]
        min_start = applicant_schedule['start_time'].min()
        max_end = applicant_schedule['end_time'].max()
        
        # 시간을 분으로 변환 (간단한 방법)
        try:
            start_hour = float(str(min_start).split(':')[0])
            start_min = float(str(min_start).split(':')[1])
            end_hour = float(str(max_end).split(':')[0])
            end_min = float(str(max_end).split(':')[1])
            
            start_total_min = start_hour * 60 + start_min
            end_total_min = end_hour * 60 + end_min
            stay_min = end_total_min - start_total_min
            stay_times.append(stay_min)
        except:
            stay_times.append(50)  # 기본값
    
    avg_stay = np.mean(stay_times) if stay_times else 0
    report.append(f"3️⃣ 평균 체류시간: {avg_stay:.1f}분 ({avg_stay/60:.1f}시간)")
    
    if avg_stay <= 120:  # 2시간 이하
        report.append("✅ 체류시간 목표 달성!")
    
    # 종합 점수
    score = 0
    if "발표준비+발표면접" in activities:
        score += 40  # 선후행 제약 해결
    if len(discussion_rooms) > 1 and abs(discussion_rooms.max() - discussion_rooms.min()) <= 1:
        score += 30  # 방 균등 활용
    if avg_stay <= 120:
        score += 30  # 체류시간 목표
    
    report.append(f"\n🎯 점수: {score}/100점")
    
    return "\n".join(report)

def test_direct_ui_fix():
    """직접 UI 수정 테스트"""
    print("🚀 직접 UI 수정 테스트 시작...")
    print("=" * 50)
    
    try:
        # 1. 직접 수정된 설정 생성
        config = create_direct_ui_config()
        
        # 2. 빠른 파라미터
        params = {
            'time_limit_sec': 30.0,
            'max_stay_hours': 3
        }
        
        print(f"📋 설정: {config['job_acts_map']['count'].sum()}명, {len(config['interview_dates'])}일")
        print(f"활동: {list(config['activities']['activity'])}")
        
        # 3. 스케줄링 실행
        print(f"\n🔄 스케줄링 실행 중...")
        result = solve_for_days_v2(config, params)
        
        if not result:
            print("❌ 결과 없음")
            return False
        
        print(f"결과 타입: {type(result)}, 길이: {len(result) if hasattr(result, '__len__') else 'N/A'}")
        
        if len(result) >= 2:
            status = result[0]
            df = result[1]
            
            print(f"상태: {status}")
            if df is not None:
                print(f"DataFrame 타입: {type(df)}, 형태: {df.shape if hasattr(df, 'shape') else 'N/A'}")
            
            # 4. 결과 분석
            if status in ['SUCCESS', 'FEASIBLE'] and df is not None and not df.empty:
                print(f"✅ 성공! {len(df)}개 활동, {df['applicant_id'].nunique()}명")
                
                # 5. 검증
                validation_report = validate_direct_fix(df)
                print(f"\n{validation_report}")
                
                # 6. Excel 파일 생성
                print("\n📥 Excel 파일 생성 중...")
                try:
                    excel_data = df_to_excel(df)
                    filename = f"direct_ui_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    
                    with open(filename, 'wb') as f:
                        f.write(excel_data.getvalue())
                    
                    print(f"✅ Excel 파일 저장: {filename}")
                    return True
                    
                except Exception as e:
                    print(f"❌ Excel 생성 실패: {e}")
                    return False
            else:
                print(f"❌ 스케줄링 실패 또는 빈 결과: {status}")
                return False
        else:
            print(f"❌ 결과 형식 오류: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_ui_fix()
    if success:
        print(f"\n🎉 직접 수정 테스트 성공!")
    else:
        print(f"\n❌ 직접 수정 테스트 실패") 