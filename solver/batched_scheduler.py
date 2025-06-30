"""
Level 2: Batched 활동 스케줄링
그룹 단위로 시간과 방을 배정하며, 직무별 방 접미사 일관성을 유지
"""
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import time as time_module
import random

from .types import (
    Group, DateConfig, Level2Result, ScheduleItem, TimeSlot,
    Room, Activity, ActivityMode, PrecedenceRule,
    GroupScheduleResult, GroupAssignment
)


class BatchedScheduler:
    """Batched 활동을 스케줄링하는 클래스"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def schedule(
        self,
        groups: Dict[str, List[Group]],
        config: DateConfig,
        time_limit: float = 60.0
    ) -> Optional[Level2Result]:
        """Level 2: Batched 활동 스케줄링"""
        self.logger.info("Batched 활동 스케줄링 시작")
        start_time = time_module.time()
        
        # Batched 활동만 필터링
        batched_activities = [
            a for a in config.activities 
            if a.mode == ActivityMode.BATCHED
        ]
        
        if not batched_activities:
            self.logger.info("Batched 활동이 없습니다")
            return Level2Result(
                schedule=[],
                room_assignments={},
                group_results=[]
            )
        
        # Precedence에 따라 활동 순서 정렬
        ordered_activities = self._order_activities_by_precedence(
            batched_activities, config.precedence_rules
        )
        
        # 스케줄링 시도
        results = []
        room_assignments = {}
        group_activity_times = {}  # 모든 활동에서 공유
        
        for activity in ordered_activities:
            result = self._schedule_activity_with_precedence(
                activity, groups, config, group_activity_times,
                time_limit - (time_module.time() - start_time)
            )
            
            if not result:
                self.logger.error(f"활동 {activity.name} 스케줄링 실패")
                return None
                
            results.append(result)
            
            # 방 배정 정보 통합 (GroupAssignment에서 추출)
            for assignment in result.assignments:
                room_assignments[f"{activity.name}_{assignment.group.id}"] = assignment.room
        
        # 전체 스케줄 통합 (GroupAssignment에서 ScheduleItem 생성)
        all_schedule = []
        for result in results:
            self.logger.info(f"🔍 처리할 활동 결과: {result.activity_name}, 배정 수: {len(result.assignments)}")
            for assignment in result.assignments:
                self.logger.info(f"🔍 그룹 처리: {assignment.group.id}, 크기: {assignment.group.size}, 실제 지원자: {len(assignment.group.applicants)}")
                
                # 🔧 수정: 그룹의 각 지원자에 대해 올바른 ScheduleItem 생성
                for i, applicant in enumerate(assignment.group.applicants):
                    schedule_item = ScheduleItem(
                        applicant_id=applicant.id,
                        job_code=applicant.job_code,  # 지원자의 실제 job_code 사용
                        activity_name=assignment.group.activity_name,
                        room_name=assignment.room.name,
                        start_time=assignment.start_time,
                        end_time=assignment.end_time,
                        group_id=assignment.group.id
                    )
                    all_schedule.append(schedule_item)
                    self.logger.debug(f"  - 지원자 {i+1}: {applicant.id} → ScheduleItem 생성")
                
                # 더미 지원자 처리 (그룹 크기 맞추기용)
                if hasattr(assignment.group, 'dummy_ids'):
                    for dummy_id in assignment.group.dummy_ids:
                        schedule_item = ScheduleItem(
                            applicant_id=dummy_id,
                            job_code=assignment.group.job_code,  # 그룹의 job_code 사용
                            activity_name=assignment.group.activity_name,
                            room_name=assignment.room.name,
                            start_time=assignment.start_time,
                            end_time=assignment.end_time,
                            group_id=assignment.group.id
                        )
                        all_schedule.append(schedule_item)
                        self.logger.debug(f"  - 더미: {dummy_id} → ScheduleItem 생성")
        
        self.logger.info(f"🔍 총 생성된 ScheduleItem 수: {len(all_schedule)}")
        
        elapsed = time_module.time() - start_time
        self.logger.info(f"Batched 스케줄링 완료: {elapsed:.1f}초")
        
        return Level2Result(
            schedule=all_schedule,
            room_assignments=room_assignments,
            group_results=results
        )
    
    def _order_activities_by_precedence(
        self,
        activities: List[Activity],
        precedence_rules: List[PrecedenceRule]
    ) -> List[Activity]:
        """Precedence 규칙에 따라 활동 순서 정렬 (위상 정렬)"""
        # 활동 이름 -> Activity 매핑
        activity_map = {a.name: a for a in activities}
        activity_names = [a.name for a in activities]
        
        # 의존성 그래프 구성
        dependencies = defaultdict(set)  # successor -> {predecessors}
        dependents = defaultdict(set)     # predecessor -> {successors}
        
        for rule in precedence_rules:
            if rule.predecessor in activity_names and rule.successor in activity_names:
                dependencies[rule.successor].add(rule.predecessor)
                dependents[rule.predecessor].add(rule.successor)
        
        # 위상 정렬
        no_deps = [name for name in activity_names if name not in dependencies]
        ordered_names = []
        
        while no_deps:
            # 알파벳 순으로 정렬하여 일관성 유지
            no_deps.sort()
            current = no_deps.pop(0)
            ordered_names.append(current)
            
            # 의존성 해결
            for dependent in dependents[current]:
                dependencies[dependent].discard(current)
                if not dependencies[dependent]:
                    no_deps.append(dependent)
        
        # 나머지 활동 추가 (순환 참조가 있는 경우)
        for name in activity_names:
            if name not in ordered_names:
                ordered_names.append(name)
                
        # Activity 객체 리스트로 변환
        return [activity_map[name] for name in ordered_names]
    
    def _schedule_activity_with_precedence(
        self,
        activity: Activity,
        groups: Dict[str, List[Group]],
        config: DateConfig,
        group_activity_times: Dict[Tuple[str, str], timedelta],
        time_limit: float
    ) -> Optional[GroupScheduleResult]:
        """Precedence를 고려한 특정 Batched 활동 스케줄링"""
        # 기존 _schedule_activity의 내용을 여기로 이동하고
        # group_activity_times를 파라미터로 받아서 사용
        
        # 해당 활동의 그룹들만 추출
        activity_groups = groups.get(activity.name, [])
        if not activity_groups:
            self.logger.warning(f"활동 {activity.name}에 대한 그룹이 없습니다")
            return None
        
        # 직무별로 그룹 분류
        groups_by_job = defaultdict(list)
        for group in activity_groups:
            groups_by_job[group.job_code].append(group)
        
        # 사용 가능한 방 찾기
        available_rooms = [
            room for room in config.rooms
            if any(rt in room.room_type for rt in activity.required_rooms)
            and room.capacity >= activity.min_capacity
        ]
        
        if not available_rooms:
            self.logger.error(f"활동 {activity.name}에 사용 가능한 방이 없습니다")
            return None
        
        # 스케줄링 시작
        assignments = []  # 🔧 수정: 딕셔너리 대신 리스트 사용
        applicant_assignments = {}  # 지원자별 assignment 추적용
        schedule_by_applicant = defaultdict(list)
        schedule_by_room = defaultdict(list)
        room_assignments = {}
        
        # 직무별 방 할당
        job_codes = list(groups_by_job.keys())
        room_suffix_map = self._assign_room_suffixes(job_codes, available_rooms)
        
        # 각 직무별로 그룹 스케줄링
        all_groups = []  # 모든 그룹을 모아서 처리
        for job_code, job_groups in groups_by_job.items():
            room_suffix = room_suffix_map.get(job_code, 'A')
            
            # 해당 접미사를 가진 방들 찾기 (여러 개일 수 있음)
            assigned_rooms = []
            for room in available_rooms:
                if room.get_suffix() == room_suffix:
                    assigned_rooms.append(room)
                    
            if not assigned_rooms:
                # 접미사가 일치하는 방이 없으면 모든 방 사용 가능
                assigned_rooms = available_rooms
            
            # 각 그룹에 대해 정보 준비
            for group in job_groups:
                all_groups.append((group, job_code, assigned_rooms))
        
        # 시간대별로 그룹 스케줄링 (병렬 처리)
        current_slot_groups = []
        next_start_time = config.operating_hours[0]
        
        for group_info in all_groups:
            group, job_code, rooms = group_info
            
            # Precedence 제약에 따른 최소 시작 시간 계산
            earliest_start = config.operating_hours[0]
            
            # 이 활동의 precedence 제약 확인
            for rule in config.precedence_rules:
                if rule.successor == activity.name:
                    # 이 그룹이 선행 활동을 완료했는지 확인
                    pred_key = (group.id, rule.predecessor)
                    if pred_key in group_activity_times:
                        pred_end_time = group_activity_times[pred_key]
                        
                        # is_adjacent 플래그에 따른 간격 처리
                        if rule.is_adjacent:
                            # 연속 배치: 정확히 지정된 간격 사용
                            required_start = pred_end_time + timedelta(minutes=rule.gap_min)
                        else:
                            # 일반 선후행: max(rule.gap_min, global_gap_min) 사용
                            global_gap = getattr(config, 'global_gap_min', 5)
                            effective_gap = max(rule.gap_min, global_gap)
                            required_start = pred_end_time + timedelta(minutes=effective_gap)
                        
                        earliest_start = max(earliest_start, required_start)
                        
                        gap_type = "연속배치" if rule.is_adjacent else "일반"
                        actual_gap = (required_start - pred_end_time).total_seconds() / 60
                        self.logger.info(
                            f"Precedence 적용: {group.id}의 {rule.predecessor} "
                            f"→ {actual_gap:.0f}분 → {activity.name} ({gap_type})"
                        )
            
            # 현재 시간대에 배치할 수 있는지 확인
            start_time = max(earliest_start, next_start_time)
            end_time = start_time + activity.duration
            
            # 운영 시간 내인지 확인
            if end_time > config.operating_hours[1]:
                # 다음 시간대로 이동
                if current_slot_groups:
                    # 현재 시간대 마무리
                    next_start_time = start_time + activity.duration + timedelta(minutes=10)
                    current_slot_groups = []
                    
                    # 새로운 시작 시간으로 재계산
                    start_time = max(earliest_start, next_start_time)
                    end_time = start_time + activity.duration
                    
                    if end_time > config.operating_hours[1]:
                        self.logger.warning(f"그룹 {group.id}가 운영 시간을 초과합니다")
                        return None
                else:
                    self.logger.warning(f"그룹 {group.id}가 운영 시간을 초과합니다")
                    return None
            
            # 사용 가능한 방 찾기
            assigned_room = None
            for room in rooms:
                # 해당 시간대에 비어있는 방 확인
                is_available = True
                for existing_slot in schedule_by_room.get(room.name, []):
                    if not (end_time <= existing_slot.start_time or start_time >= existing_slot.end_time):
                        is_available = False
                        break
                
                if is_available:
                    assigned_room = room
                    break
            
            if not assigned_room:
                # 사용 가능한 방이 없으면 다음 시간대로
                if len(current_slot_groups) < len(available_rooms):
                    # 다른 방 시도
                    for room in available_rooms:
                        if room not in rooms:
                            is_available = True
                            for existing_slot in schedule_by_room.get(room.name, []):
                                if not (end_time <= existing_slot.start_time or start_time >= existing_slot.end_time):
                                    is_available = False
                                    break
                            
                            if is_available:
                                assigned_room = room
                                break
                
                if not assigned_room:
                    # 모든 방이 사용중이면 다음 시간대로
                    next_start_time = start_time + activity.duration + timedelta(minutes=10)
                    current_slot_groups = []
                    continue
            
            # 그룹의 지원자 ID 리스트 생성
            applicant_ids = [app.id for app in group.applicants]
            if hasattr(group, 'dummy_ids'):
                applicant_ids.extend(group.dummy_ids)
            
            # TimeSlot 생성 (단일 지원자ID만 지원하므로 대표 ID 사용)
            representative_id = applicant_ids[0] if applicant_ids else None
            time_slot = TimeSlot(
                activity_name=activity.name,
                start_time=start_time,
                end_time=end_time,
                room_name=assigned_room.name,
                applicant_id=representative_id,
                group_id=group.id
            )
            
            # GroupAssignment 생성
            assignment = GroupAssignment(
                group=group,
                room=assigned_room,
                start_time=start_time,
                end_time=end_time
            )
            
            # 🔧 수정: assignments 리스트에 한 번만 추가
            assignments.append(assignment)
            
            # 결과 저장 - 지원자별 정보만 저장
            for member_id in applicant_ids:
                key = f"{member_id}_{activity.name}"
                applicant_assignments[key] = assignment
                schedule_by_applicant[member_id].append(time_slot)
            
            schedule_by_room[assigned_room.name].append(time_slot)
            room_assignments[group.id] = assigned_room.name
            
            # 그룹 활동 완료 시간 저장
            group_activity_times[(group.id, activity.name)] = end_time
            
            # 현재 시간대 그룹에 추가
            current_slot_groups.append(group)
        
        # 🔧 수정: assignments 리스트 직접 사용
        return GroupScheduleResult(
            activity_name=activity.name,
            assignments=assignments,
            success=True,
            schedule_by_applicant=dict(schedule_by_applicant),
            schedule_by_room=dict(schedule_by_room)
        )
    
    def _assign_room_suffixes(
        self, 
        job_codes: List[str],
        rooms: List[Room]
    ) -> Dict[str, str]:
        """직무별로 일관된 방 접미사 할당"""
        # 사용 가능한 접미사 추출
        suffixes = set()
        for room in rooms:
            suffix = room.get_suffix()
            if suffix:  # 빈 문자열이 아닌 경우만
                suffixes.add(suffix)
        
        # 접미사가 없는 경우 자동 생성
        if not suffixes:
            suffixes = {chr(ord('A') + i) for i in range(len(job_codes))}
        
        # 직무별 접미사 할당
        sorted_jobs = sorted(job_codes)
        sorted_suffixes = sorted(suffixes)
        
        assignments = {}
        for i, job_code in enumerate(sorted_jobs):
            if i < len(sorted_suffixes):
                assignments[job_code] = sorted_suffixes[i]
            else:
                # 접미사가 부족한 경우 순환 할당
                assignments[job_code] = sorted_suffixes[i % len(sorted_suffixes)]
        
        return assignments 

    def _update_group_times(
        self, 
        groups: Dict[str, List[Group]], 
        group_times: Dict[Tuple[str, str], timedelta]
    ) -> None:
        """그룹 활동 시간을 다른 활동에서도 참조할 수 있도록 저장"""
        # 이 메서드는 실제로는 클래스 변수나 다른 방식으로 구현해야 함
        # 현재는 단순화를 위해 비워둠
        pass 