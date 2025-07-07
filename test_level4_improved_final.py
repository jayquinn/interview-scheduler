#!/usr/bin/env python3
"""
Level 4 후처리 조정 - 최종 개선 버전 테스트

개선사항:
1. 하드코딩 문제 해결 (Batched 활동 일반화)
2. 동적 체류시간 기준 (3시간 기준 적용)
3. 리스크 분석 및 성능 최적화
4. UI 지표 개선
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime, timedelta
from solver.multi_date_scheduler import MultiDateScheduler
from solver.types import DateConfig, Room, Activity, ActivityMode, ScheduleItem, ScheduleContext
from solver.level4_post_processor import Level4PostProcessor
import pandas as pd
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_config():
    """테스트용 설정 생성"""
    
    # 방 정보
    rooms = [
        Room(name="토론면접실A", capacity=6, room_type="토론면접"),
        Room(name="토론면접실B", capacity=6, room_type="토론면접"),
        Room(name="개별면접실1", capacity=1, room_type="개별면접"),
        Room(name="개별면접실2", capacity=1, room_type="개별면접"),
        Room(name="개별면접실3", capacity=1, room_type="개별면접"),
        Room(name="발표실A", capacity=1, room_type="발표"),
        Room(name="발표실B", capacity=1, room_type="발표"),
        Room(name="대기실", capacity=50, room_type="대기"),
    ]
    
    # 활동 정보 (하드코딩 없이 일반화)
    activities = [
        Activity(
            name="집단면접",  # 토론면접 대신 집단면접
            mode=ActivityMode.BATCHED,
            duration_min=60,
            room_type="토론면접",
            min_capacity=4,
            max_capacity=6
        ),
        Activity(
            name="개별면접",
            mode=ActivityMode.INDIVIDUAL,
            duration_min=20,
            room_type="개별면접",
            min_capacity=1,
            max_capacity=1
        ),
        Activity(
            name="발표준비",
            mode=ActivityMode.INDIVIDUAL,
            duration_min=30,
            room_type="발표",
            min_capacity=1,
            max_capacity=1
        ),
        Activity(
            name="발표면접",
            mode=ActivityMode.INDIVIDUAL,
            duration_min=10,
            room_type="발표",
            min_capacity=1,
            max_capacity=1
        ),
    ]
    
    # 선행 규칙
    precedence_rules = [
        ("발표준비", "발표면접"),
    ]
    
    # 날짜별 설정
    test_dates = [
        date(2025, 7, 7),
        date(2025, 7, 8),
        date(2025, 7, 9),
        date(2025, 7, 10),
    ]
    
    date_configs = []
    for test_date in test_dates:
        config = DateConfig(
            date=datetime.combine(test_date, datetime.min.time()),
            jobs={"JOB01": 12, "JOB02": 18, "JOB03": 8},  # 날짜별 지원자 수
            operating_hours=(timedelta(hours=9), timedelta(hours=17)),
            rooms=rooms,
            activities=activities,
            precedence_rules=precedence_rules
        )
        date_configs.append(config)
    
    return date_configs

def test_level4_comprehensive():
    """Level 4 후처리 조정 종합 테스트"""
    
    print("🚀 Level 4 후처리 조정 - 최종 개선 버전 테스트")
    print("=" * 80)
    
    # 설정 생성
    date_configs = create_test_config()
    
    # 멀티데이트 스케줄러 생성
    scheduler = MultiDateScheduler()
    
    # 컨텍스트 생성
    context = ScheduleContext(
        enable_level4_optimization=True,
        level4_max_groups=4,
        level4_stay_time_threshold=3.0,  # 3시간 기준 적용
        level4_improvement_threshold=0.3,  # 0.3시간 이상 개선 가능 시
        max_stay_hours=8,
        optimization_mode="aggressive"
    )
    
    print(f"📊 테스트 설정:")
    print(f"   날짜 수: {len(date_configs)}일")
    print(f"   전체 지원자: {sum(sum(config.jobs.values()) for config in date_configs)}명")
    print(f"   Level 4 활성화: {context.enable_level4_optimization}")
    print(f"   체류시간 임계값: {context.level4_stay_time_threshold}시간")
    print(f"   개선 임계값: {context.level4_improvement_threshold}시간")
    print(f"   최대 조정 그룹: {context.level4_max_groups}개")
    
    # Level 4 ON 테스트
    print(f"\n🔧 Level 4 후처리 조정 ON 테스트")
    print("-" * 50)
    
    try:
        result_on = scheduler.schedule(date_configs, context)
        
        if result_on.success:
            print(f"✅ 스케줄링 성공!")
            
            # 체류시간 분석
            schedule_items = []
            for date_result in result_on.date_results:
                schedule_items.extend(date_result.schedule)
            
            stay_analysis = analyze_stay_times_comprehensive(schedule_items)
            
            print(f"\n📊 체류시간 분석 결과:")
            print(f"   분석 대상: {stay_analysis['total_applicants']}명")
            print(f"   평균 체류시간: {stay_analysis['avg_stay_time']:.1f}시간")
            print(f"   최대 체류시간: {stay_analysis['max_stay_time']:.1f}시간")
            print(f"   최소 체류시간: {stay_analysis['min_stay_time']:.1f}시간")
            print(f"   3시간 이상: {stay_analysis['over_3h_count']}명 ({stay_analysis['over_3h_percent']:.1f}%)")
            print(f"   4시간 이상: {stay_analysis['over_4h_count']}명 ({stay_analysis['over_4h_percent']:.1f}%)")
            print(f"   5시간 이상: {stay_analysis['over_5h_count']}명 ({stay_analysis['over_5h_percent']:.1f}%)")
            
            # Level 4 후처리 결과 분석
            if result_on.level4_results:
                print(f"\n🎯 Level 4 후처리 조정 결과:")
                total_improvement = 0
                total_groups = 0
                
                for date_str, level4_result in result_on.level4_results.items():
                    if level4_result.success:
                        print(f"   {date_str}: {level4_result.total_improvement_hours:.1f}시간 개선 "
                              f"({level4_result.adjusted_groups}개 그룹)")
                        total_improvement += level4_result.total_improvement_hours
                        total_groups += level4_result.adjusted_groups
                
                print(f"   전체 개선 효과: {total_improvement:.1f}시간 ({total_groups}개 그룹)")
                
                # 개선 효과 검증
                if total_improvement > 0:
                    print(f"✅ Level 4 후처리 조정이 성공적으로 작동했습니다!")
                else:
                    print(f"ℹ️ Level 4 후처리 조정 대상이 없었습니다.")
            
            # 날짜별 상세 분석
            print(f"\n📅 날짜별 상세 분석:")
            for i, date_result in enumerate(result_on.date_results):
                if date_result.success:
                    date_stay_analysis = analyze_single_date_stay_times(date_result.schedule)
                    print(f"   {date_configs[i].date.strftime('%Y-%m-%d')}: "
                          f"{date_stay_analysis['count']}명, "
                          f"평균 {date_stay_analysis['avg']:.1f}h, "
                          f"최대 {date_stay_analysis['max']:.1f}h")
                          
            # 안전성 검증
            safety_check = verify_safety_constraints(schedule_items)
            if safety_check['safe']:
                print(f"\n✅ 안전성 검증 통과!")
            else:
                print(f"\n⚠️ 안전성 검증 실패: {safety_check['issues']}")
                
            # 결과 저장
            save_results(result_on, stay_analysis)
            
        else:
            print(f"❌ 스케줄링 실패: {result_on.error}")
            
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🎉 Level 4 후처리 조정 테스트 완료!")

def analyze_stay_times_comprehensive(schedule_items):
    """종합적인 체류시간 분석"""
    
    from collections import defaultdict
    
    # 지원자별 스케줄 그룹화
    applicant_schedules = defaultdict(list)
    for item in schedule_items:
        if not item.applicant_id.startswith('dummy'):
            applicant_schedules[item.applicant_id].append(item)
    
    stay_times = []
    
    for applicant_id, items in applicant_schedules.items():
        if len(items) >= 2:
            items.sort(key=lambda x: x.start_time)
            first_start = items[0].start_time
            last_end = items[-1].end_time
            stay_time = (last_end - first_start).total_seconds() / 3600
            stay_times.append(stay_time)
    
    if not stay_times:
        return {'total_applicants': 0}
    
    # 통계 계산
    total = len(stay_times)
    avg = sum(stay_times) / total
    max_stay = max(stay_times)
    min_stay = min(stay_times)
    
    # 기준별 분석
    over_3h = len([t for t in stay_times if t >= 3.0])
    over_4h = len([t for t in stay_times if t >= 4.0])
    over_5h = len([t for t in stay_times if t >= 5.0])
    
    return {
        'total_applicants': total,
        'avg_stay_time': avg,
        'max_stay_time': max_stay,
        'min_stay_time': min_stay,
        'over_3h_count': over_3h,
        'over_3h_percent': over_3h / total * 100,
        'over_4h_count': over_4h,
        'over_4h_percent': over_4h / total * 100,
        'over_5h_count': over_5h,
        'over_5h_percent': over_5h / total * 100,
        'stay_times': stay_times
    }

def analyze_single_date_stay_times(schedule_items):
    """단일 날짜 체류시간 분석"""
    
    from collections import defaultdict
    
    applicant_schedules = defaultdict(list)
    for item in schedule_items:
        if not item.applicant_id.startswith('dummy'):
            applicant_schedules[item.applicant_id].append(item)
    
    stay_times = []
    
    for applicant_id, items in applicant_schedules.items():
        if len(items) >= 2:
            items.sort(key=lambda x: x.start_time)
            first_start = items[0].start_time
            last_end = items[-1].end_time
            stay_time = (last_end - first_start).total_seconds() / 3600
            stay_times.append(stay_time)
    
    if not stay_times:
        return {'count': 0, 'avg': 0, 'max': 0, 'min': 0}
    
    return {
        'count': len(stay_times),
        'avg': sum(stay_times) / len(stay_times),
        'max': max(stay_times),
        'min': min(stay_times)
    }

def verify_safety_constraints(schedule_items):
    """안전성 제약 조건 검증"""
    
    issues = []
    
    # 1. 그룹 크기 검증
    from collections import defaultdict
    group_sizes = defaultdict(int)
    group_activities = defaultdict(str)
    
    for item in schedule_items:
        if item.group_id and not item.applicant_id.startswith('dummy'):
            group_sizes[item.group_id] += 1
            group_activities[item.group_id] = item.activity_name
    
    for group_id, size in group_sizes.items():
        activity_name = group_activities[group_id]
        if "집단면접" in activity_name and size > 6:
            issues.append(f"집단면접 그룹 {group_id} 크기 초과: {size}명")
    
    # 2. 시간-방 충돌 검증
    time_room_occupancy = defaultdict(list)
    for item in schedule_items:
        if not item.applicant_id.startswith('dummy'):
            key = (item.room_name, item.start_time, item.end_time)
            time_room_occupancy[key].append(item.group_id)
    
    for (room, start, end), group_ids in time_room_occupancy.items():
        unique_groups = set(group_ids)
        if len(unique_groups) > 1:
            issues.append(f"시간-방 충돌: {room} {start} - 그룹 {unique_groups}")
    
    return {
        'safe': len(issues) == 0,
        'issues': issues
    }

def save_results(result, stay_analysis):
    """결과 저장"""
    
    from datetime import datetime
    
    # 스케줄 DataFrame 생성
    schedule_data = []
    for date_result in result.date_results:
        for item in date_result.schedule:
            schedule_data.append({
                'applicant_id': item.applicant_id,
                'job_code': item.job_code,
                'activity_name': item.activity_name,
                'room_name': item.room_name,
                'start_time': str(item.start_time),
                'end_time': str(item.end_time),
                'group_id': item.group_id,
                'interview_date': date_result.config.date.strftime('%Y-%m-%d')
            })
    
    schedule_df = pd.DataFrame(schedule_data)
    
    # 체류시간 분석 DataFrame 생성
    stay_data = []
    for i, stay_time in enumerate(stay_analysis.get('stay_times', [])):
        stay_data.append({
            'applicant_id': f'applicant_{i}',
            'stay_time_hours': stay_time,
            'over_3h': stay_time >= 3.0,
            'over_4h': stay_time >= 4.0,
            'over_5h': stay_time >= 5.0
        })
    
    stay_df = pd.DataFrame(stay_data)
    
    # 파일 저장
    filename = f"level4_improved_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(filename) as writer:
        schedule_df.to_excel(writer, sheet_name='Schedule', index=False)
        stay_df.to_excel(writer, sheet_name='StayTime', index=False)
    
    print(f"💾 결과 저장: {filename}")

if __name__ == "__main__":
    test_level4_comprehensive() 