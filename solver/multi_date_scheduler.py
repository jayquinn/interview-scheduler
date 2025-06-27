"""
멀티 날짜 스케줄러 - 전체 스케줄링 프로세스 관리
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time, timedelta
import logging
import traceback

from .types import (
    DatePlan, DateConfig, GlobalConfig, MultiDateResult, SingleDateResult,
    Activity, ActivityMode, Room, PrecedenceRule, Applicant
)
from .single_date_scheduler import SingleDateScheduler


class MultiDateScheduler:
    """여러 날짜에 걸친 면접 스케줄링을 관리하는 메인 클래스"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def schedule(
        self,
        date_plans: Dict[datetime, DatePlan],
        global_config: GlobalConfig,
        rooms: Dict[str, Dict],  # 기존 방 설정 형식
        activities: Dict[str, Dict],  # 기존 활동 설정 형식
        context: Optional["SchedulingContext"] = None
    ) -> MultiDateResult:
        """
        여러 날짜에 걸친 면접 스케줄링 실행
        
        Args:
            date_plans: 날짜별 계획 (직무/인원/활동)
            global_config: 전역 설정
            rooms: 방 정보
            activities: 활동 정보
            
        Returns:
            MultiDateResult: 전체 결과
        """
        self.logger.info(f"멀티 날짜 스케줄링 시작: {len(date_plans)}개 날짜")
        
        # 결과 저장용
        results = {}
        failed_dates = []
        total_applicants = 0
        scheduled_applicants = 0
        
        # 날짜별로 순차 처리
        for date in sorted(date_plans.keys()):
            date_plan = date_plans[date]
            total_applicants += date_plan.get_total_applicants()
            
            try:
                # 날짜별 설정 구성
                date_config = self._build_date_config(
                    date_plan, global_config, rooms, activities
                )
                
                # 단일 날짜 스케줄링
                scheduler = SingleDateScheduler(self.logger)
                result = scheduler.schedule(date_config, context)
                
                results[date] = result
                
                if result.status == "SUCCESS":
                    # 더미 제외한 실제 스케줄된 인원 계산
                    scheduled_count = len(set(
                        item.applicant_id 
                        for item in result.schedule 
                        if not item.applicant_id.startswith("DUMMY_")
                    ))
                    scheduled_applicants += scheduled_count
                    self.logger.info(f"{date.date()}: 성공 - {scheduled_count}명 스케줄링")
                else:
                    failed_dates.append(date)
                    self.logger.error(f"{date.date()}: 실패 - {result.error_message}")
                    
            except Exception as e:
                # 예외 발생시 해당 날짜 실패 처리
                error_msg = f"예외 발생: {str(e)}\n{traceback.format_exc()}"
                self.logger.error(f"{date.date()}: {error_msg}")
                
                results[date] = SingleDateResult(
                    date=date,
                    status="FAILED",
                    error_message=error_msg
                )
                failed_dates.append(date)
        
        # 전체 상태 결정
        if not failed_dates:
            status = "SUCCESS"
        elif scheduled_applicants > 0:
            status = "PARTIAL"
        else:
            status = "FAILED"
            
        return MultiDateResult(
            status=status,
            results=results,
            total_applicants=total_applicants,
            scheduled_applicants=scheduled_applicants,
            failed_dates=failed_dates
        )
    
    def _build_date_config(
        self,
        date_plan: DatePlan,
        global_config: GlobalConfig,
        rooms: Dict,
        activities: Dict
    ) -> DateConfig:
        """
        DatePlan과 전역 설정을 합쳐서 DateConfig 생성
        오버라이드 로직 적용
        """
        # 기본값은 전역 설정에서
        operating_hours = global_config.operating_hours.get("default", (time(9, 0), time(17, 30)))
        precedence_rules = global_config.precedence_rules.copy()
        
        # 날짜별 오버라이드 적용
        if date_plan.overrides:
            if "operating_hours" in date_plan.overrides:
                hours = date_plan.overrides["operating_hours"]
                start_time = time.fromisoformat(hours["start"])
                end_time = time.fromisoformat(hours["end"])
                operating_hours = (start_time, end_time)
            
            if "precedence" in date_plan.overrides:
                # 오버라이드된 선후행 규칙으로 교체
                precedence_rules = [
                    PrecedenceRule(
                        predecessor=rule[0],
                        successor=rule[1],
                        gap_min=rule[2] if len(rule) > 2 else 0,
                        is_adjacent=rule[3] if len(rule) > 3 else False
                    )
                    for rule in date_plan.overrides["precedence"]
                ]
        
        # 활동 객체 생성
        activity_objects = {}
        for act_name in date_plan.selected_activities:
            if act_name in activities:
                act_data = activities[act_name]
                mode_str = act_data.get("mode", "individual")
                
                # 문자열을 ActivityMode Enum으로 변환
                mode_map = {
                    "individual": ActivityMode.INDIVIDUAL,
                    "parallel": ActivityMode.PARALLEL,
                    "batched": ActivityMode.BATCHED
                }
                mode = mode_map.get(mode_str, ActivityMode.INDIVIDUAL)
                
                room_type = act_data.get("room_type", "기본실")
                activity_objects[act_name] = Activity(
                    name=act_name,
                    mode=mode,
                    duration_min=act_data.get("duration_min", 30),
                    room_type=room_type,
                    min_capacity=act_data.get("min_capacity", 1),
                    max_capacity=act_data.get("max_capacity", 1),
                    required_rooms=[room_type]  # required_rooms 설정
                )
        
        # 방 객체 생성
        room_objects = []
        room_types_used = set(act.room_type for act in activity_objects.values())
        
        for room_type in room_types_used:
            if room_type in rooms:
                room_data = rooms[room_type]
                count = room_data.get("count", 1)
                capacity = room_data.get("capacity", 1)
                
                # 방이 여러 개면 A, B, C... 접미사 추가
                if count > 1:
                    for i in range(count):
                        suffix = chr(ord('A') + i)
                        room_objects.append(Room(
                            name=f"{room_type}{suffix}",
                            room_type=room_type,
                            capacity=capacity
                        ))
                else:
                    room_objects.append(Room(
                        name=room_type,
                        room_type=room_type,
                        capacity=capacity
                    ))
        
        # 직무-활동 매트릭스 생성
        job_activity_matrix = {}
        # 기본적으로 모든 직무가 모든 선택된 활동 수행
        for job_code in date_plan.jobs.keys():
            for activity in date_plan.selected_activities:
                job_activity_matrix[(job_code, activity)] = True
        
        # 직무별 오버라이드 적용 (있다면)
        if date_plan.overrides and "job_activities" in date_plan.overrides:
            job_activities = date_plan.overrides["job_activities"]
            for job_code, activities in job_activities.items():
                # 해당 직무의 모든 활동을 False로 리셋
                for activity in date_plan.selected_activities:
                    job_activity_matrix[(job_code, activity)] = False
                # 선택된 활동만 True로 설정
                for activity in activities:
                    job_activity_matrix[(job_code, activity)] = True
        
        # time을 timedelta로 변환
        start_td = timedelta(
            hours=operating_hours[0].hour,
            minutes=operating_hours[0].minute
        )
        end_td = timedelta(
            hours=operating_hours[1].hour,
            minutes=operating_hours[1].minute
        )
        
        return DateConfig(
            date=date_plan.date,
            jobs=date_plan.jobs,
            activities=list(activity_objects.values()),  # Dict를 List로 변환
            rooms=room_objects,
            operating_hours=(start_td, end_td),
            precedence_rules=precedence_rules,
            job_activity_matrix=job_activity_matrix,
            global_gap_min=global_config.global_gap_min
        )
    
    def validate_config(
        self,
        date_plans: Dict[datetime, DatePlan],
        global_config: GlobalConfig
    ) -> List[str]:
        """
        설정 검증 - 실행 전에 명백한 오류 체크
        
        Returns:
            오류 메시지 리스트 (비어있으면 검증 통과)
        """
        errors = []
        
        # 1. 날짜 중복 체크 (이미 Dict이므로 자동으로 중복 없음)
        
        # 2. 순환 참조 체크
        for rule in global_config.precedence_rules:
            if rule.predecessor == rule.successor:
                errors.append(f"순환 참조: {rule.predecessor} → {rule.successor}")
        
        # 3. 그룹 크기 일관성 체크
        for act_name, (min_size, max_size) in global_config.batched_group_sizes.items():
            if min_size > max_size:
                errors.append(f"{act_name}: 최소 크기({min_size})가 최대 크기({max_size})보다 큽니다")
            if min_size <= 0:
                errors.append(f"{act_name}: 최소 크기는 1 이상이어야 합니다")
        
        # 4. 운영시간 유효성 체크
        for name, (start, end) in global_config.operating_hours.items():
            if start >= end:
                errors.append(f"운영시간 오류 ({name}): 시작시간이 종료시간보다 늦습니다")
        
        return errors 