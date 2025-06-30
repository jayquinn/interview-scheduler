#!/usr/bin/env python3
"""
그룹 생성 과정 디버깅 스크립트
Batched 스케줄링에서 중복이 발생하는 원인을 파악합니다.
"""

from test_app_default_data import create_app_default_data
from solver.api import solve_for_days_v2
import core

def debug_group_creation():
    """그룹 생성 과정을 단계별로 디버깅"""
    
    print("🔧 그룹 생성 과정 디버깅 시작...")
    
    # 디폴트 데이터 생성
    session_state = create_app_default_data()
    cfg = core.build_config(session_state)
    
    # 스케줄러 실행 전에 그룹 생성 과정 직접 확인
    try:
        from solver.multi_date_scheduler import MultiDateScheduler
        from solver.single_date_scheduler import SingleDateScheduler
        from solver.group_optimizer_v2 import GroupOptimizerV2
        from solver.types import Applicant, ActivityMode
        from datetime import date
        
        # 스케줄링 실행으로 내부 로직 추적
        from solver.api import _convert_ui_data
        
        logs_buffer = []
        date_plans, global_config, rooms, activities = _convert_ui_data(cfg, logs_buffer)
        
        print(f"\n📋 변환된 설정:")
        print(f"  - 날짜 계획: {len(date_plans)}개")
        for date, plan in date_plans.items():
            print(f"    * {date.date()}: {plan.jobs} (활동: {plan.selected_activities})")
        
        # 첫 번째 날짜의 설정 가져오기
        target_date = list(date_plans.keys())[0]
        date_plan = date_plans[target_date]
        
        # DateConfig 생성
        scheduler = MultiDateScheduler()
        date_config = scheduler._build_date_config(date_plan, global_config, rooms, activities)
        
        print(f"\n📋 Date Config:")
        print(f"  - 활동 수: {len(date_config.activities)}")
        for activity in date_config.activities:
            print(f"    * {activity.name} ({activity.mode.value})")
        print(f"  - 방 수: {len(date_config.rooms)}")
        for room in date_config.rooms:
            print(f"    * {room.name} ({room.capacity}명)")
        print(f"  - 직무별 지원자:")
        for job, count in date_config.jobs.items():
            print(f"    * {job}: {count}명")
        
        # 지원자 생성
        applicants = _create_applicants(date_config)
        print(f"\n👥 생성된 지원자:")
        print(f"  - 총 지원자 수: {len(applicants)}")
        for applicant in applicants:
            print(f"    * {applicant.id} ({applicant.job_code}): {applicant.required_activities}")
        
        # 그룹 최적화 실행
        print(f"\n🔍 그룹 최적화 시작...")
        optimizer = GroupOptimizerV2()
        level1_result = optimizer.optimize(
            applicants=applicants,
            activities=date_config.activities,
            time_limit=30.0
        )
        
        if level1_result:
            print(f"✅ 그룹 최적화 성공:")
            print(f"  - 총 그룹 수: {level1_result.group_count}")
            print(f"  - 더미 지원자 수: {level1_result.dummy_count}")
            print(f"  - 활동별 그룹:")
            
            for activity_name, groups in level1_result.groups.items():
                print(f"\n    {activity_name}:")
                for i, group in enumerate(groups):
                    print(f"      그룹 {i+1} (ID: {group.id}):")
                    print(f"        - 크기: {group.size}")
                    print(f"        - 지원자 수: {len(group.applicants)}")
                    print(f"        - 지원자 목록:")
                    for applicant in group.applicants:
                        print(f"          * {applicant.id}")
                    
                    # 중복 지원자 확인
                    applicant_ids = [app.id for app in group.applicants]
                    unique_ids = set(applicant_ids)
                    if len(applicant_ids) != len(unique_ids):
                        print(f"        ❌ 중복 지원자 발견!")
                        from collections import Counter
                        duplicates = Counter(applicant_ids)
                        for app_id, count in duplicates.items():
                            if count > 1:
                                print(f"          - {app_id}: {count}번")
                    else:
                        print(f"        ✅ 중복 지원자 없음")
                    
                    # 더미 지원자 확인
                    if hasattr(group, 'dummy_ids'):
                        print(f"        - 더미 지원자: {group.dummy_ids}")
            
            # 전체 지원자 중복 확인
            print(f"\n🔍 전체 지원자 중복 확인:")
            all_applicants_in_groups = []
            for groups in level1_result.groups.values():
                for group in groups:
                    for applicant in group.applicants:
                        all_applicants_in_groups.append(applicant.id)
            
            from collections import Counter
            applicant_counts = Counter(all_applicants_in_groups)
            duplicates_found = {app_id: count for app_id, count in applicant_counts.items() if count > 1}
            
            if duplicates_found:
                print(f"❌ 전체 중복 지원자 발견: {len(duplicates_found)}명")
                for app_id, count in duplicates_found.items():
                    print(f"  - {app_id}: {count}번 등장")
            else:
                print(f"✅ 전체 중복 지원자 없음")
        else:
            print(f"❌ 그룹 최적화 실패")
            return
            
        # Batched 스케줄링 실행
        print(f"\n🚀 Batched 스케줄링 시작...")
        from solver.batched_scheduler import BatchedScheduler
        
        batched_scheduler = BatchedScheduler()
        level2_result = batched_scheduler.schedule(
            groups=level1_result.groups,
            config=date_config,
            time_limit=30.0
        )
        
        if level2_result:
            print(f"✅ Batched 스케줄링 성공:")
            print(f"  - 총 스케줄 항목: {len(level2_result.schedule)}")
            
            # 지원자별 스케줄 개수 확인
            from collections import Counter
            applicant_schedule_counts = Counter([item.applicant_id for item in level2_result.schedule])
            
            print(f"  - 지원자별 스케줄 개수:")
            for app_id, count in applicant_schedule_counts.items():
                print(f"    * {app_id}: {count}개")
                if count > 1:
                    print(f"      ❌ 중복 스케줄 발견!")
                    # 해당 지원자의 스케줄 상세 확인
                    app_schedules = [item for item in level2_result.schedule if item.applicant_id == app_id]
                    for schedule in app_schedules:
                        print(f"        - {schedule.activity_name} {schedule.room_name} {schedule.start_time}~{schedule.end_time} (그룹: {schedule.group_id})")
        else:
            print(f"❌ Batched 스케줄링 실패")
    
    except Exception as e:
        print(f"❌ 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_group_creation() 