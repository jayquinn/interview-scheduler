#!/usr/bin/env python3
"""
앱 기본 데이터를 사용한 스케줄러 테스트
app.py의 기본 설정값들을 그대로 사용해서 테스트합니다.
"""

import pandas as pd
from datetime import date, time
import sys
import traceback

def create_app_default_data():
    """app.py의 기본 데이터를 생성"""
    print("🔧 앱 기본 데이터 생성 중...")
    
    # 1. 기본 활동 (app.py 라인 77-83)
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 2. 기본 선후행 제약 (app.py 라인 95-97) + 토론면접 순서 추가
    precedence = pd.DataFrame([
        {"predecessor": "토론면접", "successor": "발표준비+발표면접", "gap_min": 5, "adjacent": False},
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 3. 기본 운영 시간 (app.py 라인 100-101)
    oper_start_time = time(9, 0)
    oper_end_time = time(17, 30)
    
    # 4. 기본 방 템플릿 (app.py 라인 104-109)
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 5. 기본 직무 데이터 (단일 날짜용)
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [20],
        "토론면접": [True],
        "발표준비": [True], 
        "발표면접": [True]
    })
    
    # 6. 멀티데이트 플랜 (app.py 라인 124-156) - 간단화
    multidate_plans = {
        "2025-07-01": {
            "date": date(2025, 7, 1),
            "enabled": True,
            "jobs": [{"code": "JOB01", "count": 6}]  # 테스트용으로 작은 수로 변경
        }
    }
    
    # 7. 집단면접 설정
    group_min_size = 4
    group_max_size = 6
    global_gap_min = 5
    max_stay_hours = 5
    
    # 방 계획 생성 (room_template 기반으로 자동 생성)
    final_plan_dict = {}
    for rt, values in room_template.items():
        final_plan_dict[f"{rt}_count"] = values['count']
        final_plan_dict[f"{rt}_cap"] = values['cap']
    room_plan = pd.DataFrame([final_plan_dict])
    
    # 운영 시간 생성
    oper_window_dict = {
        "start_time": oper_start_time.strftime("%H:%M"),
        "end_time": oper_end_time.strftime("%H:%M")
    }
    oper_window = pd.DataFrame([oper_window_dict])
    
    # 세션 상태 시뮬레이션
    session_state = {
        "activities": activities,
        "precedence": precedence,
        "oper_start_time": oper_start_time,
        "oper_end_time": oper_end_time,
        "room_template": room_template,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "job_acts_map": job_acts_map,
        "multidate_plans": multidate_plans,
        "group_min_size": group_min_size,
        "group_max_size": group_max_size,
        "global_gap_min": global_gap_min,
        "max_stay_hours": max_stay_hours,
        "interview_dates": [date(2025, 7, 1)]
    }
    
    print("✅ 기본 데이터 생성 완료")
    return session_state

def test_config_building(session_state):
    """config 빌드 테스트"""
    print("\n🔧 Config 빌드 테스트...")
    
    try:
        import core
        cfg = core.build_config(session_state)
        print(f"✅ Config 빌드 성공")
        
        # Config 내용 확인 
        print(f"  - 총 설정 수: {len(cfg)}")
        for key, value in cfg.items():
            if isinstance(value, pd.DataFrame):
                print(f"  - {key}: DataFrame ({len(value)} rows)")
            else:
                print(f"  - {key}: {type(value)} - {value}")
            
        return cfg
    
    except Exception as e:
        print(f"❌ Config 빌드 실패: {e}")
        traceback.print_exc()
        return None

def test_scheduler_v2(cfg, params):
    """계층적 스케줄러 v2 테스트"""
    print("\n🚀 계층적 스케줄러 v2 테스트...")
    
    try:
        from solver.api import solve_for_days_v2
        
        status, final_wide, logs, limit = solve_for_days_v2(cfg, params, debug=True)
        
        print(f"Status: {status}")
        print(f"Daily Limit: {limit}")
        print(f"Schedule Count: {len(final_wide) if final_wide is not None else 0}")
        
        if final_wide is not None and not final_wide.empty:
            print("✅ v2 스케줄러 성공!")
            print(f"첫 5행:\n{final_wide.head()}")
        else:
            print("❌ v2 스케줄러 실패 - 빈 결과")
            
        print(f"\n로그:\n{logs}")
        
        return status == "SUCCESS", final_wide
        
    except Exception as e:
        print(f"❌ v2 스케줄러 오류: {e}")
        traceback.print_exc()
        return False, None

def test_individual_components():
    """개별 컴포넌트 테스트"""
    print("\n🔍 개별 컴포넌트 테스트...")
    
    try:
        # 1. Types 임포트 테스트
        print("1. Types 임포트...")
        from solver.types import DatePlan, GlobalConfig, MultiDateResult
        print("   ✅ Types 임포트 성공")
        
        # 2. API 임포트 테스트  
        print("2. API 임포트...")
        from solver.api import solve_for_days_v2
        print("   ✅ API 임포트 성공")
        
        # 3. 기본 클래스 생성 테스트
        print("3. 기본 클래스 생성...")
        from solver.types import Activity, Room, Applicant, Group, ActivityMode
        
        activity = Activity(name="토론면접", mode=ActivityMode.BATCHED, duration_min=30, room_type="토론면접실")
        room = Room(name="토론면접실A", capacity=6, room_type="토론면접실")
        applicant = Applicant(id="TEST001", job_code="JOB01", required_activities=["토론면접"])
        group = Group(id="G001", job_code="JOB01", applicants=[applicant], size=1, activity_name="토론면접")
        
        print("   ✅ 기본 클래스 생성 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ 컴포넌트 테스트 실패: {e}")
        traceback.print_exc()
        return False

def main():
    """메인 테스트 실행"""
    print("="*60)
    print("🧪 앱 기본 데이터 스케줄러 테스트")
    print("="*60)
    
    # 1. 개별 컴포넌트 테스트
    if not test_individual_components():
        print("❌ 개별 컴포넌트 테스트 실패 - 중단")
        return
    
    # 2. 기본 데이터 생성
    session_state = create_app_default_data()
    
    # 3. Config 빌드
    cfg = test_config_building(session_state)
    if not cfg:
        print("❌ Config 빌드 실패 - 중단")
        return
    
    # 4. 파라미터 설정
    params = {
        "min_gap_min": session_state.get('global_gap_min', 5),
        "time_limit_sec": 30,  # 테스트용으로 짧게
        "max_stay_hours": session_state.get('max_stay_hours', 8),
        "group_min_size": session_state.get('group_min_size', 4),
        "group_max_size": session_state.get('group_max_size', 6)
    }
    
    print(f"\n📋 테스트 파라미터:")
    for k, v in params.items():
        print(f"  - {k}: {v}")
    
    # 5. 스케줄러 테스트
    success, result = test_scheduler_v2(cfg, params)
    
    if success:
        print("\n🎉 전체 테스트 성공!")
        
        # 6. 엑셀 파일 생성 및 분석
        print("\n📊 엑셀 파일 생성 및 분석...")
        
        try:
            from app import df_to_excel
            from io import BytesIO
            
            # 엑셀 파일 생성
            excel_buffer = BytesIO()
            df_to_excel(result, stream=excel_buffer)
            
            # 파일로 저장
            excel_filename = "test_schedule_result.xlsx"
            with open(excel_filename, "wb") as f:
                f.write(excel_buffer.getvalue())
            
            print(f"✅ 엑셀 파일 생성 완료: {excel_filename}")
            
            # 결과 분석
            print("\n📈 결과 분석:")
            print(f"  - 총 스케줄 항목: {len(result)}개")
            print(f"  - 지원자 수: {result['applicant_id'].nunique()}명")
            print(f"  - 활동 종류: {result['activity_name'].unique()}")
            print(f"  - 방 종류: {result['room_name'].unique()}")
            
            # 중복 확인
            print("\n🔍 중복 확인:")
            duplicates = result.groupby(['applicant_id', 'start_time', 'end_time']).size()
            duplicates = duplicates[duplicates > 1]
            if len(duplicates) > 0:
                print(f"❌ 시간 중복 발견: {len(duplicates)}건")
                for (applicant, start, end), count in duplicates.items():
                    print(f"  - {applicant}: {start}~{end} ({count}개 중복)")
            else:
                print("✅ 시간 중복 없음")
            
            # 그룹 크기 분석
            print("\n📊 그룹 크기 분석:")
            group_analysis = result.groupby(['activity_name', 'room_name', 'start_time', 'end_time']).size()
            print("활동별 그룹 크기:")
            for (activity, room, start, end), size in group_analysis.items():
                print(f"  - {activity} ({room}): {start}~{end} → {size}명")
            
        except Exception as e:
            print(f"❌ 엑셀 파일 생성 실패: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ 전체 테스트 실패")
    
    print("="*60)

if __name__ == "__main__":
    main() 