#!/usr/bin/env python3
"""
🎯 Simple Interview Scheduler - Standalone Test
Streamlit 없이 단순한 Python 스크립트로 테스트
"""

import sys
import logging
from datetime import datetime, time, timedelta
import pandas as pd

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_scheduler():
    """SimpleInterviewScheduler 직접 테스트"""
    
    try:
        # 모듈 import
        from simple_scheduler import SimpleInterviewScheduler, Activity, Room, Applicant, PrecedenceRule
        
        print("🚀 SimpleInterviewScheduler 테스트 시작")
        
        # 테스트 데이터 생성
        activities = [
            Activity("서류검토", "individual", 30, "회의실"),
            Activity("면접", "individual", 60, "면접실"),
            Activity("그룹토론", "batched", 90, "대회의실", min_cap=3, max_cap=5)
        ]
        
        rooms = [
            Room("회의실A", "회의실", 4, datetime(2024, 1, 15)),
            Room("면접실1", "면접실", 2, datetime(2024, 1, 15)),
            Room("대회의실", "대회의실", 10, datetime(2024, 1, 15))
        ]
        
        applicants = [
            Applicant("A001", "JOB1", ["서류검토", "면접", "그룹토론"], datetime(2024, 1, 15)),
            Applicant("A002", "JOB1", ["서류검토", "면접", "그룹토론"], datetime(2024, 1, 15)),
            Applicant("A003", "JOB1", ["서류검토", "면접", "그룹토론"], datetime(2024, 1, 15))
        ]
        
        precedence_rules = [
            PrecedenceRule("서류검토", "면접", gap_min=15),
            PrecedenceRule("면접", "그룹토론", gap_min=30)
        ]
        
        operating_hours = (time(9, 0), time(18, 0))
        params = {"max_stay_hours": 8}
        
        # 스케줄러 생성 및 실행
        scheduler = SimpleInterviewScheduler(logger)
        status, results, logs = scheduler.schedule(
            applicants, activities, rooms, precedence_rules, operating_hours, params
        )
        
        print(f"\n📊 테스트 결과:")
        print(f"상태: {status}")
        print(f"결과 수: {len(results)}")
        print(f"로그: {logs}")
        
        if results:
            print(f"\n📋 스케줄 결과:")
            for result in results:
                print(f"  {result.applicant_id} - {result.activity_name} - {result.room_name} - "
                      f"{result.start_time} ~ {result.end_time}")
        
        print("\n✅ 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_core_simple():
    """core_simple 모듈 테스트"""
    
    try:
        print("\n🔧 core_simple 모듈 테스트 시작")
        
        # 테스트용 데이터프레임 생성
        activities_df = pd.DataFrame({
            'activity_name': ['서류검토', '면접', '그룹토론'],
            'mode': ['individual', 'individual', 'batched'],
            'duration_min': [30, 60, 90],
            'room_type': ['회의실', '면접실', '대회의실'],
            'min_cap': [1, 1, 3],
            'max_cap': [1, 1, 5]
        })
        
        precedence_df = pd.DataFrame({
            'predecessor': ['서류검토', '면접'],
            'successor': ['면접', '그룹토론'],
            'gap_min': [15, 30],
            'is_adjacent': [False, False]
        })
        
        room_plan_df = pd.DataFrame({
            'room_name': ['회의실A', '면접실1', '대회의실'],
            'room_type': ['회의실', '면접실', '대회의실'],
            'capacity': [4, 2, 10],
            'date': ['2024-01-15', '2024-01-15', '2024-01-15']
        })
        
        oper_window_df = pd.DataFrame({
            'date': ['2024-01-15'],
            'start_time': ['09:00'],
            'end_time': ['18:00']
        })
        
        multidate_plans_df = pd.DataFrame({
            'date': ['2024-01-15'],
            'job_code': ['JOB1'],
            'applicant_count': [3]
        })
        
        job_acts_map_df = pd.DataFrame({
            'job_code': ['JOB1', 'JOB1', 'JOB1'],
            'activity_name': ['서류검토', '면접', '그룹토론'],
            'count': [3, 3, 3]
        })
        
        # core_simple import 및 테스트
        from core_simple import run_simple_scheduler, to_excel_simple
        
        config = {
            'activities': activities_df,
            'precedence': precedence_df,
            'room_plan': room_plan_df,
            'oper_window': oper_window_df,
            'multidate_plans': multidate_plans_df,
            'job_acts_map': job_acts_map_df
        }
        
        status, result_df, logs = run_simple_scheduler(config)
        
        print(f"상태: {status}")
        print(f"결과 데이터프레임 크기: {result_df.shape if result_df is not None else 'None'}")
        print(f"로그: {logs}")
        
        if result_df is not None and not result_df.empty:
            print(f"\n📋 결과 데이터프레임:")
            print(result_df.head())
            # 엑셀로 저장 (기존 포맷)
            excel_bytes = to_excel_simple(result_df)
            with open("test_simple_result.xlsx", "wb") as f:
                f.write(excel_bytes)
            print("✅ 엑셀 파일로 저장 완료: test_simple_result.xlsx")
        else:
            print("❌ 결과 데이터프레임이 비어 있습니다.")
        
        print("✅ core_simple 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ core_simple 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 Simple Interview Scheduler - Standalone Test")
    print("=" * 50)
    
    # 두 가지 테스트 실행
    test1_success = test_simple_scheduler()
    test2_success = test_core_simple()
    
    print("\n" + "=" * 50)
    print("📊 최종 테스트 결과:")
    print(f"SimpleInterviewScheduler 테스트: {'✅ 성공' if test1_success else '❌ 실패'}")
    print(f"core_simple 테스트: {'✅ 성공' if test2_success else '❌ 실패'}")
    
    if test1_success and test2_success:
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        sys.exit(0)
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        sys.exit(1) 