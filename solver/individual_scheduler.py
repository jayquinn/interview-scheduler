"""
Level 3: Individual & Parallel 활동 스케줄링

Individual: 1명씩 개별 면접
Parallel: 여러명이 같은 공간에서 각자 다른 일
"""
import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import timedelta
from collections import defaultdict
from ortools.sat.python import cp_model

from .types import (
    Activity, Room, Applicant, Group, ActivityMode,
    GroupScheduleResult, IndividualScheduleResult, 
    TimeSlot, GroupAssignment, RoomAssignment,
    PrecedenceRule
)

logger = logging.getLogger(__name__)


class IndividualScheduler:
    """Level 3: Individual & Parallel 활동 스케줄러"""
    
    def __init__(self):
        self.time_slot_minutes = 5  # 5분 단위
        
    def schedule_individuals(
        self,
        applicants: List[Applicant],
        activities: List[Activity], 
        rooms: List[Room],
        batched_results: List[GroupScheduleResult],
        start_time: timedelta,
        end_time: timedelta,
        date_str: str,
        precedence_rules: List[PrecedenceRule] = None,
        global_gap_min: int = 5
    ) -> Optional[IndividualScheduleResult]:
        """Individual & Parallel 활동 스케줄링"""
        
        # 디버깅: applicants 타입 확인
        logger.debug(f"Applicants 수: {len(applicants)}")
        if applicants:
            logger.debug(f"첫 번째 applicant 타입: {type(applicants[0])}")
            logger.debug(f"첫 번째 applicant: {applicants[0]}")
        
        # Individual/Parallel 활동만 필터링
        individual_activities = [
            a for a in activities 
            if a.mode in [ActivityMode.INDIVIDUAL, ActivityMode.PARALLEL]
        ]
        
        if not individual_activities:
            logger.info("Individual/Parallel 활동이 없습니다")
            return IndividualScheduleResult(
                assignments={},
                schedule_by_applicant={},
                schedule_by_room={},
                success=True
            )
            
        # 1. 휴리스틱 방식 시도
        logger.info("휴리스틱 방식으로 Individual 스케줄링 시도...")
        result = self._schedule_heuristic(
            applicants, individual_activities, rooms, 
            batched_results, start_time, end_time, date_str,
            precedence_rules or [], global_gap_min
        )
        
        if result and result.success:
            logger.info("✅ 휴리스틱 방식 성공")
            return result
            
        # 2. 실패시 CP-SAT 방식 시도
        logger.warning("휴리스틱 실패, CP-SAT 방식 시도...")
        result = self._schedule_cpsat(
            applicants, individual_activities, rooms,
            batched_results, start_time, end_time, date_str
        )
        
        if result and result.success:
            logger.info("✅ CP-SAT 방식 성공")
            return result
            
        logger.error("❌ Individual 스케줄링 실패")
        return None
        
    def _schedule_heuristic(
        self,
        applicants: List[Applicant],
        activities: List[Activity],
        rooms: List[Room],
        batched_results: List[GroupScheduleResult],
        start_time: timedelta,
        end_time: timedelta,
        date_str: str,
        precedence_rules: List[PrecedenceRule],
        global_gap_min: int = 5
    ) -> Optional[IndividualScheduleResult]:
        """휴리스틱 방식 Individual 스케줄링 - 개선된 순서 최적화"""
        
        # Batched 활동의 시간대 추출
        batched_blocks = self._extract_batched_blocks(batched_results)
        
        # 방별 사용 가능 시간대 계산
        room_availability = self._calculate_room_availability(
            rooms, batched_blocks, start_time, end_time
        )
        
        # 지원자별 스케줄 저장
        assignments = {}
        schedule_by_applicant = defaultdict(list)
        schedule_by_room = defaultdict(list)
        
        # ✨ 개선된 스케줄링 순서 결정
        ordered_activities = self._optimize_activity_order(
            activities, precedence_rules, applicants
        )
        
        # ✨ 백트래킹 기반 스케줄링 시도
        success = self._schedule_with_backtracking(
            ordered_activities, applicants, rooms, room_availability,
            batched_blocks, assignments, schedule_by_applicant,
            schedule_by_room, date_str, precedence_rules,
            start_time, end_time, global_gap_min
        )
        
        if not success:
            logger.warning("백트래킹 스케줄링 실패, 기본 방식으로 재시도")
            # 기본 방식으로 재시도
            assignments.clear()
            schedule_by_applicant.clear()
            schedule_by_room.clear()
            
            # 방 가용성 재계산
            room_availability = self._calculate_room_availability(
                rooms, batched_blocks, start_time, end_time
            )
            
            # 활동별로 처리 (기본 방식)
            for activity in ordered_activities:
                if activity.mode == ActivityMode.INDIVIDUAL:
                    success = self._schedule_individual_activity(
                        activity, applicants, rooms, room_availability,
                        batched_blocks, assignments, schedule_by_applicant,
                        schedule_by_room, date_str, precedence_rules,
                        start_time, end_time, global_gap_min, activities
                    )
                else:  # PARALLEL
                    success = self._schedule_parallel_activity(
                        activity, applicants, rooms, room_availability,
                        batched_blocks, assignments, schedule_by_applicant,
                        schedule_by_room, date_str, start_time, end_time,
                        precedence_rules, global_gap_min, activities
                    )
                    
                if not success:
                    logger.warning(f"활동 {activity.name} 스케줄링 실패")
                    return None
                
        return IndividualScheduleResult(
            assignments=assignments,
            schedule_by_applicant=dict(schedule_by_applicant),
            schedule_by_room=dict(schedule_by_room),
            success=True
        )
        
    def _schedule_with_backtracking(
        self,
        activities: List[Activity],
        applicants: List[Applicant],
        rooms: List[Room],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        precedence_rules: List[PrecedenceRule],
        start_time: timedelta,
        end_time: timedelta,
        global_gap_min: int
    ) -> bool:
        """🧠 개선된 백트래킹 기반 스케줄링"""
        
        # precedence 체인이 있는 활동들을 우선 처리
        precedence_pairs = []
        for rule in precedence_rules:
            if rule.is_adjacent:  # 연속배치가 필요한 경우만
                precedence_pairs.append((rule.predecessor, rule.successor))
        
        if not precedence_pairs:
            # precedence가 없으면 기본 방식 사용
            return self._schedule_activities_basic(
                activities, applicants, rooms, room_availability,
                batched_blocks, assignments, schedule_by_applicant,
                schedule_by_room, date_str, precedence_rules,
                start_time, end_time, global_gap_min, activities
            )
        
        logger.info("🚀 백트래킹 기반 precedence 쌍 스케줄링 시작")
        
        # 🧠 핵심 개선: precedence 쌍을 하나의 단위로 처리
        for pred_name, succ_name in precedence_pairs:
            pred_activity = next((a for a in activities if a.name == pred_name), None)
            succ_activity = next((a for a in activities if a.name == succ_name), None)
            
            if not pred_activity or not succ_activity:
                logger.error(f"precedence 쌍의 활동을 찾을 수 없음: {pred_name} → {succ_name}")
                return False
            
            # 🎯 통합 스케줄링: 발표준비+발표면접을 함께 처리
            success = self._schedule_precedence_pair_integrated(
                pred_activity, succ_activity, applicants, rooms,
                room_availability, batched_blocks, assignments,
                schedule_by_applicant, schedule_by_room, date_str,
                precedence_rules, start_time, end_time, global_gap_min, activities
            )
            
            if not success:
                logger.error(f"precedence 쌍 스케줄링 실패: {pred_name} → {succ_name}")
                return False
        
        # 나머지 활동들 처리
        remaining_activities = [
            a for a in activities 
            if not any(a.name in [pair[0], pair[1]] for pair in precedence_pairs)
        ]
        
        for activity in remaining_activities:
            success = self._schedule_single_activity(
                activity, applicants, rooms, room_availability,
                batched_blocks, assignments, schedule_by_applicant,
                schedule_by_room, date_str, precedence_rules,
                start_time, end_time, global_gap_min, activities
            )
            
            if not success:
                logger.error(f"단일 활동 스케줄링 실패: {activity.name}")
                return False
        
        return True
    
    def _schedule_precedence_pair_integrated(
        self,
        pred_activity: Activity,  # 발표준비
        succ_activity: Activity,  # 발표면접
        applicants: List[Applicant],
        rooms: List[Room],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        precedence_rules: List[PrecedenceRule],
        start_time: timedelta,
        end_time: timedelta,
        global_gap_min: int,
        activities: List[Activity] = None
    ) -> bool:
        """🎯 통합 precedence 쌍 스케줄링"""
        
        logger.info(f"🎯 통합 스케줄링: {pred_activity.name} → {succ_activity.name}")
        
        # 대상 지원자 필터
        target_applicants = [
            a for a in applicants 
            if pred_activity.name in a.required_activities and succ_activity.name in a.required_activities
        ]
        
        if not target_applicants:
            return True
        
        # 방 찾기
        pred_rooms = self._find_available_rooms(pred_activity, rooms, room_availability)
        succ_rooms = self._find_available_rooms(succ_activity, rooms, room_availability)
        
        if not pred_rooms or not succ_rooms:
            logger.error("사용 가능한 방이 없음")
            return False
        
        # gap 시간 계산
        gap_duration = timedelta(minutes=5)  # adjacent=True이므로 정확히 5분
        for rule in precedence_rules:
            if rule.predecessor == pred_activity.name and rule.successor == succ_activity.name:
                gap_duration = timedelta(minutes=rule.gap_min)
                break
        
        # 🧠 핵심: 후속 방 수에 맞춘 그룹 크기
        max_succ_rooms = len(succ_rooms)
        pred_room = pred_rooms[0]
        optimal_group_size = min(pred_activity.max_capacity, pred_room.capacity, max_succ_rooms)
        
        logger.info(f"최적 그룹 크기: {optimal_group_size} (후속 방: {max_succ_rooms}개)")
        
        # 그룹 나누기
        groups = []
        for i in range(0, len(target_applicants), optimal_group_size):
            group = target_applicants[i:i + optimal_group_size]
            groups.append(group)
        
        # 각 그룹별로 시간 찾기 및 스케줄링
        for group_idx, group in enumerate(groups):
            success = self._schedule_group_with_successor(
                group, pred_activity, succ_activity, pred_room, succ_rooms,
                gap_duration, room_availability, batched_blocks,
                assignments, schedule_by_applicant, schedule_by_room,
                date_str, start_time, end_time, activities
            )
            
            if not success:
                logger.error(f"그룹 {group_idx + 1} 스케줄링 실패")
                return False
        
        return True
    
    def _schedule_group_with_successor(
        self,
        group: List[Applicant],
        pred_activity: Activity,
        succ_activity: Activity,
        pred_room: Room,
        succ_rooms: List[Room],
        gap_duration: timedelta,
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        start_time: timedelta,
        end_time: timedelta,
        activities: List[Activity] = None
    ) -> bool:
        """그룹과 후속 활동을 함께 스케줄링"""
        
        # 그룹 공통 가용 시간 찾기
        common_times = self._get_group_common_free_times(
            group, batched_blocks, schedule_by_applicant, start_time, end_time
        )
        
        # 가능한 시간대 찾기
        for common_start, common_end in common_times:
            for room_start, room_end in room_availability[pred_room.name]:
                # 교집합 계산
                slot_start = max(common_start, room_start)
                slot_end = min(common_end, room_end)
                
                if slot_end - slot_start >= pred_activity.duration:
                    pred_end = slot_start + pred_activity.duration
                    succ_start = pred_end + gap_duration
                    # 후속 활동의 duration을 동적으로 찾기
                    successor_duration = None
                    for act in activities:
                        if act.name == succ_activity.name:
                            successor_duration = act.duration
                            break
                    
                    if not successor_duration:
                        logger.error(f"후속 활동 {succ_activity.name}의 duration을 찾을 수 없음")
                        continue
                        
                    successor_end = succ_start + successor_duration
                    
                    # 후속 활동 방 확인
                    available_succ_rooms = []
                    for succ_room in succ_rooms[:len(group)]:  # 그룹 크기만큼만
                        for succ_room_start, succ_room_end in room_availability[succ_room.name]:
                            if succ_room_start <= succ_start and succ_room_end >= successor_end:
                                available_succ_rooms.append(succ_room)
                                break
                    
                    if len(available_succ_rooms) >= len(group):
                        # 스케줄링 실행
                        self._execute_group_schedule(
                            group, pred_activity, succ_activity, pred_room,
                            available_succ_rooms, slot_start, pred_end,
                            succ_start, successor_end, assignments,
                            schedule_by_applicant, schedule_by_room,
                            room_availability, date_str
                        )
                        return True
        
        logger.warning(f"그룹 스케줄링 실패: {[a.id for a in group]}")
        return False
    
    def _execute_group_schedule(
        self,
        group: List[Applicant],
        pred_activity: Activity,
        succ_activity: Activity,
        pred_room: Room,
        succ_rooms: List[Room],
        pred_start: timedelta,
        pred_end: timedelta,
        succ_start: timedelta,
        succ_end: timedelta,
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        date_str: str
    ):
        """그룹 스케줄 실행"""
        
        # 발표준비 스케줄 생성
        pred_slot = TimeSlot(
            activity_name=pred_activity.name,
            start_time=pred_start,
            end_time=pred_end,
            room_name=pred_room.name,
            applicant_id=group[0].id if group else None,  # 그룹의 첫 번째 지원자 ID 사용
            group_id=f"group_{pred_activity.name}_{pred_start.total_seconds()}"
        )
        
        # 발표준비 저장
        for applicant in group:
            key = f"{applicant.id}_{pred_activity.name}"
            assignments[key] = pred_slot
            schedule_by_applicant[applicant.id].append(pred_slot)
        
        schedule_by_room[pred_room.name].append(pred_slot)
        
        # 방 가용성 업데이트
        self._update_availability(
            room_availability[pred_room.name], pred_start, pred_end
        )
        
        # 발표면접 스케줄 생성
        for i, applicant in enumerate(group):
            if i < len(succ_rooms):
                succ_room = succ_rooms[i]
                
                succ_slot = TimeSlot(
                    activity_name=succ_activity.name,
                    start_time=succ_start,
                    end_time=succ_end,
                    room_name=succ_room.name,
                    applicant_id=applicant.id
                )
                
                key = f"{applicant.id}_{succ_activity.name}"
                assignments[key] = succ_slot
                schedule_by_applicant[applicant.id].append(succ_slot)
                schedule_by_room[succ_room.name].append(succ_slot)
                
                # 방 가용성 업데이트
                self._update_availability(
                    room_availability[succ_room.name], succ_start, succ_end
                )
                
                logger.info(f"✅ {applicant.id}: {pred_activity.name} {pred_start}~{pred_end} → {succ_activity.name} {succ_start}~{succ_end}")
        
        logger.info(f"✅ 그룹 스케줄링 완료: {len(group)}명")
    
    def _schedule_individual_activity(
        self,
        activity: Activity,
        applicants: List[Applicant],
        rooms: List[Room],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        precedence_rules: List[PrecedenceRule],
        start_time: timedelta = None,
        end_time: timedelta = None,
        global_gap_min: int = 5,
        activities: List[Activity] = None
    ) -> bool:
        """Individual 활동 스케줄링 (1명씩) - 후속 활동 예약 시스템 포함"""
        
        # 활동 수행 지원자 필터
        target_applicants = [
            a for a in applicants 
            if activity.name in a.required_activities
        ]
        
        # 직무별로 그룹화
        by_job = defaultdict(list)
        for applicant in target_applicants:
            by_job[applicant.job_code].append(applicant)
            
        # 직무별로 스케줄링
        for job, job_applicants in by_job.items():
            # 사용 가능한 방 찾기
            available_rooms = self._find_available_rooms(
                activity, rooms, room_availability
            )
            
            if not available_rooms:
                logger.error(f"활동 {activity.name}에 사용 가능한 방이 없음")
                return False
                
            # 라운드 로빈으로 방 배정
            room_idx = 0
            
            for applicant in job_applicants:
                # 지원자의 가용 시간 찾기
                applicant_free_times = self._get_applicant_free_times(
                    applicant, batched_blocks, schedule_by_applicant,
                    start_time, end_time
                )
                
                # Precedence 제약에 따른 최소 시작 시간 계산
                earliest_start = timedelta(hours=0)
                
                # 이미 스케줄된 활동에서 precedence 체크
                if applicant.id in schedule_by_applicant:
                    for prev_slot in schedule_by_applicant[applicant.id]:
                        # precedence 규칙 확인
                        for rule in precedence_rules:
                            if (rule.predecessor == prev_slot.activity_name and 
                                rule.successor == activity.name):
                                
                                # is_adjacent 플래그에 따른 간격 처리
                                if rule.is_adjacent:
                                    # 연속 배치: 정확히 지정된 간격 사용
                                    required_gap = timedelta(minutes=rule.gap_min)
                                else:
                                    # 일반 선후행: max(rule.gap_min, global_gap_min) 사용
                                    effective_gap = max(rule.gap_min, global_gap_min)
                                    required_gap = timedelta(minutes=effective_gap)
                                
                                required_start = prev_slot.end_time + required_gap
                                earliest_start = max(earliest_start, required_start)
                                
                                gap_type = "연속배치" if rule.is_adjacent else "일반"
                                actual_gap = required_gap.total_seconds() / 60
                                logger.info(
                                    f"Precedence: {applicant.id}의 {rule.predecessor} "
                                    f"→ {actual_gap:.0f}분 → {activity.name} ({gap_type})"
                                )
                
                # 후속 활동 예약 시스템: precedence가 있는 경우 후속 활동 시간도 함께 고려
                successor_reservation = None
                for rule in precedence_rules:
                    if rule.predecessor == activity.name and rule.is_adjacent:
                        # 연속배치가 필요한 후속 활동이 있는 경우
                        successor_activity = rule.successor
                        successor_gap = timedelta(minutes=rule.gap_min)
                        successor_duration = None
                        
                        # 후속 활동의 duration 찾기
                        for act in activities:
                            if act.name == successor_activity:
                                successor_duration = act.duration
                                break
                        
                        if successor_duration:
                            successor_reservation = {
                                'activity': successor_activity,
                                'gap': successor_gap,
                                'duration': successor_duration
                            }
                            logger.info(f"후속 활동 예약: {applicant.id}의 {activity.name} → {successor_activity}")
                
                # 방 순회하며 가능한 시간 찾기 (후속 활동 고려)
                scheduled = False
                for _ in range(len(available_rooms)):
                    room = available_rooms[room_idx % len(available_rooms)]
                    room_idx += 1
                    
                    # 방의 가용 시간과 지원자 가용 시간 교집합
                    for room_slot in room_availability[room.name]:
                        for app_slot in applicant_free_times:
                            # Precedence 고려
                            overlap_start = max(room_slot[0], app_slot[0], earliest_start)
                            overlap_end = min(room_slot[1], app_slot[1])
                            
                            if overlap_end - overlap_start >= activity.duration:
                                current_end = overlap_start + activity.duration
                                
                                # 후속 활동 예약이 있는 경우 가능한지 확인
                                if successor_reservation:
                                    successor_start = current_end + successor_reservation['gap']
                                    successor_end = successor_start + successor_reservation['duration']
                                    
                                    # 🎯 수정: 후속 활동을 위한 방 찾기 (일반화)
                                    successor_room_available = False
                                    successor_room_name = None
                                    
                                    # 후속 활동의 room_type 찾기
                                    successor_room_type = None
                                    for act in activities:
                                        if act.name == successor_reservation['activity']:
                                            successor_room_type = act.room_type
                                            break
                                    
                                    if successor_room_type:
                                        # 모든 방에서 후속 활동 방 타입 찾기
                                        for room in rooms:
                                            if room.room_type == successor_room_type:
                                                # 해당 방의 가용성 확인
                                                if room.name in room_availability:
                                                    for succ_room_slot in room_availability[room.name]:
                                                        if (succ_room_slot[0] <= successor_start and 
                                                            succ_room_slot[1] >= successor_end):
                                                            successor_room_available = True
                                                            successor_room_name = room.name
                                                            break
                                                if successor_room_available:
                                                    break
                                    
                                    if not successor_room_available:
                                        logger.debug(f"후속 활동 {successor_reservation['activity']} 시간 확보 불가: {successor_start} ~ {successor_end}")
                                        continue  # 다른 시간대 시도
                                    else:
                                        # 🎯 후속 활동 즉시 예약
                                        logger.info(f"🎉 연속배치 성공: {applicant.id} {activity.name} → {successor_reservation['activity']}")
                                        
                                        # 후속 활동 스케줄 생성
                                        successor_slot = TimeSlot(
                                            activity_name=successor_reservation['activity'],
                                            start_time=successor_start,
                                            end_time=successor_end,
                                            room_name=successor_room_name,
                                            applicant_id=applicant.id
                                        )
                                        
                                        # 후속 활동 저장
                                        succ_key = f"{applicant.id}_{successor_reservation['activity']}"
                                        assignments[succ_key] = successor_slot
                                        schedule_by_applicant[applicant.id].append(successor_slot)
                                        schedule_by_room[successor_room_name].append(successor_slot)
                                        
                                        # 후속 활동 방 가용성 업데이트
                                        self._update_availability(
                                            room_availability[successor_room_name],
                                            successor_start,
                                            successor_end
                                        )
                                
                                # 스케줄 생성
                                time_slot = TimeSlot(
                                    activity_name=activity.name,
                                    start_time=overlap_start,
                                    end_time=current_end,
                                    room_name=room.name,
                                    applicant_id=applicant.id
                                )
                                
                                # 저장
                                key = f"{applicant.id}_{activity.name}"
                                assignments[key] = time_slot
                                schedule_by_applicant[applicant.id].append(time_slot)
                                schedule_by_room[room.name].append(time_slot)
                                
                                # 방 가용성 업데이트
                                self._update_availability(
                                    room_availability[room.name],
                                    overlap_start, 
                                    current_end
                                )
                                
                                scheduled = True
                                break
                                
                        if scheduled:
                            break
                    
                    if scheduled:  # 이미 스케줄됐으면 다른 방에서 다시 스케줄하지 않음
                        break
                            
                if not scheduled:
                    logger.warning(f"지원자 {applicant.id}의 {activity.name} 스케줄링 실패")
                    return False
                    
        return True
        
    def _schedule_parallel_activity(
        self,
        activity: Activity,
        applicants: List[Applicant],
        rooms: List[Room],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        start_time: timedelta = None,
        end_time: timedelta = None,
        precedence_rules: List[PrecedenceRule] = None,
        global_gap_min: int = 5,
        activities: List[Activity] = None
    ) -> bool:
        """Parallel 활동 스케줄링 - 🧠 스마트 그룹핑"""
        
        # 활동 수행 지원자 필터
        target_applicants = [
            a for a in applicants 
            if activity.name in a.required_activities
        ]
        
        if not target_applicants:
            return True  # 대상자가 없으면 성공
        
        # 사용 가능한 방 찾기 (최소 1명 이상 수용 가능한 방)
        available_rooms = self._find_available_rooms(
            activity, rooms, room_availability
        )
        
        if not available_rooms:
            logger.error(f"활동 {activity.name}에 사용 가능한 방이 없음")
            return False
            
        # 가장 큰 방 선택
        room = max(available_rooms, key=lambda r: r.capacity)
        
        # 🧠 스마트 그룹핑: 후속 활동 방 수를 고려한 그룹 크기 결정
        if precedence_rules and self._has_adjacent_successor(activity.name, precedence_rules):
            successor_room_count = self._get_successor_room_count(activity.name, precedence_rules, rooms, activities)
            optimal_group_size = min(room.capacity, activity.max_capacity, successor_room_count)
            logger.info(f"🧠 스마트 그룹핑: 후속 방 {successor_room_count}개에 맞춰 그룹 크기 {optimal_group_size}로 조정")
        else:
            optimal_group_size = min(room.capacity, activity.max_capacity)
        
        # 지원자를 최적 그룹으로 나누기
        applicant_groups = []
        for i in range(0, len(target_applicants), optimal_group_size):
            group = target_applicants[i:i + optimal_group_size]
            applicant_groups.append(group)
        
        logger.info(f"활동 {activity.name}: {len(target_applicants)}명을 {len(applicant_groups)}개 그룹으로 분할 (그룹당 최대 {optimal_group_size}명)")
        
        # 🚀 핵심 개선: 연속배치 최적화
        if precedence_rules and self._has_adjacent_successor(activity.name, precedence_rules):
            logger.info(f"🔧 연속배치 최적화 모드: {activity.name}")
            return self._schedule_parallel_with_successor_optimization(
                activity, applicant_groups, room, room_availability,
                batched_blocks, assignments, schedule_by_applicant,
                schedule_by_room, date_str, precedence_rules, 
                start_time, end_time, global_gap_min, activities
            )
        
        # 기존 방식 (연속배치가 필요없는 경우)
        return self._schedule_parallel_basic(
            activity, applicant_groups, room, room_availability,
            batched_blocks, assignments, schedule_by_applicant,
            schedule_by_room, date_str, start_time, end_time
        )
    
    def _has_adjacent_successor(self, activity_name: str, precedence_rules: List[PrecedenceRule]) -> bool:
        """해당 활동에 연속배치가 필요한 후속 활동이 있는지 확인"""
        for rule in precedence_rules:
            if rule.predecessor == activity_name and rule.is_adjacent:
                return True
        return False
    
    def _schedule_parallel_with_successor_optimization(
        self,
        activity: Activity,
        applicant_groups: List[List[Applicant]],
        room: Room,
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        precedence_rules: List[PrecedenceRule],
        start_time: timedelta,
        end_time: timedelta,
        global_gap_min: int,
        activities: List[Activity] = None
    ) -> bool:
        """🚀 연속배치 최적화된 Parallel 스케줄링"""
        
        # 후속 활동 정보 찾기
        successor_info = None
        for rule in precedence_rules:
            if rule.predecessor == activity.name and rule.is_adjacent:
                successor_info = {
                    'name': rule.successor,
                    'gap': timedelta(minutes=rule.gap_min)
                }
                break
        
        if not successor_info:
            logger.warning("연속배치 정보를 찾을 수 없음")
            return False
        
        logger.info(f"연속배치 목표: {activity.name} → {successor_info['gap'].total_seconds()/60:.0f}분 → {successor_info['name']}")
        
        # 🎯 핵심: 각 그룹별로 연속 시간 확보
        for group_idx, group in enumerate(applicant_groups):
            # 그룹 내 모든 지원자의 공통 가용 시간 찾기
            group_free_times = self._get_group_common_free_times(
                group, batched_blocks, schedule_by_applicant, start_time, end_time
            )
            
            if not group_free_times:
                logger.warning(f"그룹 {group_idx + 1}: 공통 가용 시간 없음")
                return False
            
            # 연속 시간 확보 시도
            scheduled = False
            for room_slot in room_availability[room.name]:
                for common_slot in group_free_times:
                    # 현재 활동 시간 계산
                    current_start = max(room_slot[0], common_slot[0])
                    current_end = current_start + activity.duration
                    
                    if current_end > min(room_slot[1], common_slot[1]):
                        continue  # 시간 부족
                    
                    # 후속 활동 시간 계산
                    successor_start = current_end + successor_info['gap']
                    # 후속 활동의 duration을 동적으로 찾기
                    successor_duration = None
                    for act in activities:
                        if act.name == successor_info['name']:
                            successor_duration = act.duration
                            break
                    
                    if not successor_duration:
                        logger.error(f"후속 활동 {successor_info['name']}의 duration을 찾을 수 없음")
                        continue
                        
                    successor_end = successor_start + successor_duration
                    
                    # 후속 활동을 위한 방 확보 가능한지 확인
                    # 후속 활동의 room_type 찾기
                    successor_room_type = None
                    for act in activities:
                        if act.name == successor_info['name']:
                            successor_room_type = act.room_type
                            break
                    
                    successor_rooms_available = self._check_successor_rooms_availability(
                        group, successor_start, successor_end, room_availability, successor_room_type
                    )
                    
                    if len(successor_rooms_available) >= len(group):
                        # ✅ 연속배치 가능!
                        logger.info(f"🎉 그룹 {group_idx + 1} 연속배치 성공: {current_start} ~ {current_end} → {successor_start} ~ {successor_end}")
                        
                        # 현재 활동 스케줄 생성
                        self._create_parallel_schedule(
                            activity, group, room, current_start, current_end,
                            assignments, schedule_by_applicant, schedule_by_room, date_str
                        )
                        
                        # 후속 활동 스케줄 생성
                        self._create_successor_schedules(
                            group, successor_info['name'], successor_start, successor_end,
                            successor_rooms_available, assignments, schedule_by_applicant,
                            schedule_by_room, date_str
                        )
                        
                        # 방 가용성 업데이트
                        self._update_availability(room_availability[room.name], current_start, current_end)
                        for i, succ_room_name in enumerate(successor_rooms_available[:len(group)]):
                            self._update_availability(room_availability[succ_room_name], successor_start, successor_end)
                        
                        scheduled = True
                        break
                        
                if scheduled:
                    break
            
            if not scheduled:
                logger.warning(f"그룹 {group_idx + 1} 연속배치 실패")
                return False
        
        logger.info("🎉 모든 그룹 연속배치 완료!")
        return True
    
    def _check_successor_rooms_availability(
        self,
        group: List[Applicant],
        start_time: timedelta,
        end_time: timedelta,
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        successor_room_type: str = None
    ) -> List[str]:
        """후속 활동을 위한 방 가용성 확인"""
        available_rooms = []
        
        for room_name, slots in room_availability.items():
            # 후속 활동 방 타입이 지정된 경우 해당 타입만 확인
            if successor_room_type and successor_room_type not in room_name:
                continue
                
            for slot in slots:
                if slot[0] <= start_time and slot[1] >= end_time:
                    available_rooms.append(room_name)
                    break
        
        return available_rooms
    
    def _create_parallel_schedule(
        self,
        activity: Activity,
        group: List[Applicant],
        room: Room,
        start_time: timedelta,
        end_time: timedelta,
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str
    ):
        """Parallel 활동 스케줄 생성"""
        # 개별 지원자 스케줄
        for applicant in group:
            time_slot = TimeSlot(
                activity_name=activity.name,
                start_time=start_time,
                end_time=end_time,
                room_name=room.name,
                applicant_id=applicant.id
            )
            
            key = f"{applicant.id}_{activity.name}"
            assignments[key] = time_slot
            schedule_by_applicant[applicant.id].append(time_slot)
        
        # 방 스케줄 - 그룹 스케줄링의 경우 group_id 사용
        room_slot = TimeSlot(
            activity_name=activity.name,
            start_time=start_time,
            end_time=end_time,
            room_name=room.name,
            applicant_id=group[0].id if group else None,  # 그룹의 첫 번째 지원자 ID
            group_id=f"group_{activity.name}_{start_time.total_seconds()}"
        )
        schedule_by_room[room.name].append(room_slot)
    
    def _create_successor_schedules(
        self,
        group: List[Applicant],
        successor_name: str,
        start_time: timedelta,
        end_time: timedelta,
        available_rooms: List[str],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str
    ):
        """후속 활동 스케줄 생성 - 🔧 중복 배치 방지"""
        
        # 방 부족 시 처리
        if len(available_rooms) < len(group):
            logger.warning(f"후속 활동 {successor_name}: 방 부족 ({len(available_rooms)}개 방, {len(group)}명)")
            # 방 개수만큼만 처리하고 나머지는 다음 시간대로 미룸
            group = group[:len(available_rooms)]
        
        for i, applicant in enumerate(group):
            if i < len(available_rooms):
                room_name = available_rooms[i]
                
                time_slot = TimeSlot(
                    activity_name=successor_name,
                    start_time=start_time,
                    end_time=end_time,
                    room_name=room_name,
                    applicant_id=applicant.id
                )
                
                key = f"{applicant.id}_{successor_name}"
                assignments[key] = time_slot
                schedule_by_applicant[applicant.id].append(time_slot)
                schedule_by_room[room_name].append(time_slot)
                
                logger.debug(f"후속 활동 배치: {applicant.id} → {room_name} ({start_time} ~ {end_time})")
            else:
                logger.warning(f"후속 활동 배치 실패: {applicant.id} (방 부족)")
    
    def _schedule_parallel_basic(
        self,
        activity: Activity,
        applicant_groups: List[List[Applicant]],
        room: Room,
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        start_time: timedelta,
        end_time: timedelta
    ) -> bool:
        """기본 Parallel 스케줄링 (기존 방식)"""
        
        # 각 그룹별로 스케줄링
        current_time_cursor = None
        
        for group_idx, group in enumerate(applicant_groups):
            # 그룹 내 모든 지원자의 공통 가용 시간 찾기
            group_free_times = self._get_group_common_free_times(
                group, batched_blocks, schedule_by_applicant, start_time, end_time
            )
            
            if not group_free_times:
                logger.warning(f"그룹 {group_idx + 1}: 공통 가용 시간 없음")
                return False
            
            # 방과 시간 교집합 찾기
            scheduled = False
            for room_slot in room_availability[room.name]:
                for common_slot in group_free_times:
                    slot_start = max(room_slot[0], common_slot[0])
                    slot_end = min(room_slot[1], common_slot[1])
                    
                    if slot_end - slot_start >= activity.duration:
                        # 연속 배치를 위해 이전 그룹 종료 시간 고려
                        if current_time_cursor:
                            slot_start = max(slot_start, current_time_cursor)
                        
                        if slot_start + activity.duration <= slot_end:
                            # 스케줄 생성
                            self._create_parallel_schedule(
                                activity, group, room, slot_start, slot_start + activity.duration,
                                assignments, schedule_by_applicant, schedule_by_room, date_str
                            )
                            
                            # 방 가용성 업데이트
                            self._update_availability(
                                room_availability[room.name], 
                                slot_start, 
                                slot_start + activity.duration
                            )
                            
                            current_time_cursor = slot_start + activity.duration
                            scheduled = True
                            break
                            
                if scheduled:
                    break
            
            if not scheduled:
                logger.warning(f"그룹 {group_idx + 1} 스케줄링 실패")
                return False
        
        return True
    
    def _schedule_cpsat(
        self,
        applicants: List[Applicant],
        activities: List[Activity],
        rooms: List[Room],
        batched_results: List[GroupScheduleResult],
        start_time: timedelta,
        end_time: timedelta,
        date_str: str
    ) -> Optional[IndividualScheduleResult]:
        """🚀 개선된 CP-SAT 방식 Individual 스케줄링 - 체류시간 최소화 목적함수 포함"""
        
        model = cp_model.CpModel()
        logger.info("🔧 CP-SAT 스케줄링 시작 - 체류시간 최소화 목적함수 적용")
        
        # 시간 범위를 분 단위로 변환 (기준시간: start_time)
        horizon = int((end_time - start_time).total_seconds() / 60)
        logger.info(f"시간 범위: {start_time} ~ {end_time} ({horizon}분)")
        
        # Batched 활동 블록 추출
        batched_blocks = self._extract_batched_blocks(batched_results)
        
        # 변수 생성
        intervals = {}        # (applicant_id, activity_name) -> interval_var
        start_vars = {}       # (applicant_id, activity_name) -> start_var  
        end_vars = {}         # (applicant_id, activity_name) -> end_var
        presence_vars = {}    # (applicant_id, activity_name) -> presence_var
        room_vars = {}        # (applicant_id, activity_name, room_name) -> room_var
        
        # 🏗️ Individual 활동별 변수 생성
        for applicant in applicants:
            applicant_activities = [a for a in activities if a.name in applicant.required_activities]
                    
            for activity in applicant_activities:
                suffix = f"{applicant.id}_{activity.name}"
                duration_min = int(activity.duration.total_seconds() / 60)
                
                # 시작/종료 시간 변수
                start_var = model.NewIntVar(0, horizon - duration_min, f'start_{suffix}')
                end_var = model.NewIntVar(duration_min, horizon, f'end_{suffix}')
                presence_var = model.NewBoolVar(f'presence_{suffix}')
                
                # 일관성 제약: end = start + duration
                model.Add(end_var == start_var + duration_min).OnlyEnforceIf(presence_var)
                
                # Interval 변수
                interval_var = model.NewOptionalIntervalVar(
                    start_var, duration_min, end_var, presence_var, f'interval_{suffix}'
                )
                
                # 변수 저장
                intervals[(applicant.id, activity.name)] = interval_var
                start_vars[(applicant.id, activity.name)] = start_var
                end_vars[(applicant.id, activity.name)] = end_var
                presence_vars[(applicant.id, activity.name)] = presence_var
                
                # 방 배정 변수
                activity_rooms = [r for r in rooms if any(rt in r.room_type for rt in activity.required_rooms)]
                for room in activity_rooms:
                    room_var = model.NewBoolVar(f'room_{suffix}_{room.name}')
                    room_vars[(applicant.id, activity.name, room.name)] = room_var
                
                # 방 배정 제약: 정확히 하나의 방 선택
                if activity_rooms:
                    room_options = [room_vars[(applicant.id, activity.name, r.name)] for r in activity_rooms]
                    model.Add(sum(room_options) == 1).OnlyEnforceIf(presence_var)
        
        # 🔗 제약조건 추가
        
        # 1. 방 용량 제약 (같은 시간에 같은 방 사용 불가)
        for room in rooms:
            room_intervals = []
            for (app_id, act_name), interval in intervals.items():
                if (app_id, act_name, room.name) in room_vars:
                    # 이 방을 사용하는 경우의 interval
                    room_interval = model.NewOptionalIntervalVar(
                        start_vars[(app_id, act_name)],
                        int([a for a in activities if a.name == act_name][0].duration.total_seconds() / 60),
                        end_vars[(app_id, act_name)],
                        room_vars[(app_id, act_name, room.name)],
                        f'room_interval_{app_id}_{act_name}_{room.name}'
                    )
                    room_intervals.append(room_interval)
            
            if room_intervals:
                model.AddNoOverlap(room_intervals)
        
        # 2. Batched 활동과의 시간 충돌 방지
        for applicant in applicants:
            if applicant.id in batched_blocks:
                for batched_start, batched_end in batched_blocks[applicant.id]:
                    # Batched 시간을 분 단위로 변환
                    batched_start_min = int((batched_start - start_time).total_seconds() / 60)
                    batched_end_min = int((batched_end - start_time).total_seconds() / 60)
                    
                    # Individual 활동이 Batched 시간과 겹치지 않도록
                    for activity in activities:
                        if (applicant.id, activity.name) in intervals:
                            start_var = start_vars[(applicant.id, activity.name)]
                            end_var = end_vars[(applicant.id, activity.name)]
                            presence_var = presence_vars[(applicant.id, activity.name)]
                            
                            # 겹침 방지: end_var <= batched_start_min OR start_var >= batched_end_min
                            non_overlap_1 = model.NewBoolVar(f'no_overlap_1_{applicant.id}_{activity.name}_{batched_start_min}')
                            non_overlap_2 = model.NewBoolVar(f'no_overlap_2_{applicant.id}_{activity.name}_{batched_start_min}')
                            
                            model.Add(end_var <= batched_start_min).OnlyEnforceIf([presence_var, non_overlap_1])
                            model.Add(start_var >= batched_end_min).OnlyEnforceIf([presence_var, non_overlap_2])
                            model.AddBoolOr([non_overlap_1, non_overlap_2, presence_var.Not()])
        
        # 3. 필수 활동 제약
        for applicant in applicants:
            for activity_name in applicant.required_activities:
                if any(a.name == activity_name for a in activities):
                    presence_var = presence_vars.get((applicant.id, activity_name))
                    if presence_var:
                        model.Add(presence_var == 1)  # 필수 활동은 반드시 배정
        
        # 🎯 핵심: 체류시간 최소화 목적함수
        stay_time_vars = []
        
        for applicant in applicants:
            # 해당 지원자의 모든 활동 (Batched + Individual)
            applicant_start_times = []
            applicant_end_times = []
            
            # Individual 활동 시간
            for activity in activities:
                if (applicant.id, activity.name) in start_vars:
                    start_var = start_vars[(applicant.id, activity.name)]
                    end_var = end_vars[(applicant.id, activity.name)]
                    presence_var = presence_vars[(applicant.id, activity.name)]
                    
                    # presence가 True인 경우만 고려
                    applicant_start_times.append(start_var)
                    applicant_end_times.append(end_var)
            
            # Batched 활동 시간 추가
            if applicant.id in batched_blocks:
                for batched_start, batched_end in batched_blocks[applicant.id]:
                    batched_start_min = int((batched_start - start_time).total_seconds() / 60)
                    batched_end_min = int((batched_end - start_time).total_seconds() / 60)
                    
                    # 상수 값을 변수로 변환
                    batched_start_var = model.NewConstant(batched_start_min)
                    batched_end_var = model.NewConstant(batched_end_min)
                    
                    applicant_start_times.append(batched_start_var)
                    applicant_end_times.append(batched_end_var)
            
            # 체류시간 계산 (전체 활동이 있는 경우만)
            if applicant_start_times and applicant_end_times:
                # 첫 활동 시작시간
                first_start = model.NewIntVar(0, horizon, f'first_start_{applicant.id}')
                model.AddMinEquality(first_start, applicant_start_times)
        
                # 마지막 활동 종료시간  
                last_end = model.NewIntVar(0, horizon, f'last_end_{applicant.id}')
                model.AddMaxEquality(last_end, applicant_end_times)
                
                # 체류시간 = 마지막 종료 - 첫 시작
                stay_time = model.NewIntVar(0, horizon, f'stay_time_{applicant.id}')
                model.Add(stay_time == last_end - first_start)
                
                stay_time_vars.append(stay_time)
                
                logger.debug(f"지원자 {applicant.id}: {len(applicant_start_times)}개 활동 체류시간 변수 생성")
        
        # 🎯 목적함수: 총 체류시간 최소화
        if stay_time_vars:
            total_stay_time = model.NewIntVar(0, horizon * len(applicants), 'total_stay_time')
            model.Add(total_stay_time == sum(stay_time_vars))
            model.Minimize(total_stay_time)
            
            logger.info(f"✅ 목적함수 설정: {len(stay_time_vars)}명의 총 체류시간 최소화")
        else:
            logger.warning("⚠️ 체류시간 변수가 없어 목적함수 설정 불가")
        
        # 🚀 Solver 실행
        solver = cp_model.CpSolver()
        set_safe_cpsat_parameters(solver)
        solver.parameters.max_time_in_seconds = 60.0  # 체류시간 최적화를 위해 시간 연장
        solver.parameters.log_search_progress = True
        
        logger.info("🔍 CP-SAT 최적화 실행 중...")
        status = solver.Solve(model)
        
        # 결과 분석
        if status == cp_model.OPTIMAL:
            logger.info("✅ 최적해 발견!")
        elif status == cp_model.FEASIBLE:
            logger.info("✅ 실행 가능해 발견!")
        else:
            logger.error(f"❌ CP-SAT 실패: {solver.StatusName(status)}")
            return None
        
        # 체류시간 통계 출력
        if stay_time_vars:
            total_minutes = solver.Value(total_stay_time)
            avg_hours = total_minutes / len(stay_time_vars) / 60
            logger.info(f"📊 최적화 결과: 평균 체류시간 {avg_hours:.1f}시간")
            
            for i, applicant in enumerate(applicants):
                if i < len(stay_time_vars):
                    stay_minutes = solver.Value(stay_time_vars[i])
                    stay_hours = stay_minutes / 60
                    logger.debug(f"  {applicant.id}: {stay_hours:.1f}시간")
        
            # 결과 추출
            return self._extract_cpsat_results(
            solver, intervals, presence_vars, room_vars,
            applicants, activities, rooms, date_str, start_time
            )
        
    # Helper 메서드들
    def _extract_batched_blocks(
        self, 
        batched_results: List[GroupScheduleResult]
    ) -> Dict[str, List[Tuple[timedelta, timedelta]]]:
        """Batched 활동이 차지하는 시간대 추출"""
        blocks = defaultdict(list)
        
        for result in batched_results:
            for applicant_id, slots in result.schedule_by_applicant.items():
                for slot in slots:
                    time_block = (slot.start_time, slot.end_time)
                    blocks[applicant_id].append(time_block)
                    
        # 정렬 및 병합
        for applicant_id in blocks:
            blocks[applicant_id] = self._merge_time_blocks(blocks[applicant_id])
            
        return dict(blocks)
        
    def _calculate_room_availability(
        self,
        rooms: List[Room],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        start_time: timedelta,
        end_time: timedelta
    ) -> Dict[str, List[Tuple[timedelta, timedelta]]]:
        """방별 사용 가능 시간대 계산"""
        availability = {}
        
        for room in rooms:
            # 초기값: 전체 운영 시간
            available = [(start_time, end_time)]
            
            # Batched 활동이 사용하는 시간 제외
            # 현재는 Batched 결과에서 방 사용 정보를 추출하지 않음
            # 필요시 GroupScheduleResult의 schedule_by_room을 활용
            
            availability[room.name] = available
            
        return availability
        
    def _get_applicant_free_times(
        self,
        applicant: Applicant,
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        start_time: timedelta = None,
        end_time: timedelta = None
    ) -> List[Tuple[timedelta, timedelta]]:
        """지원자의 가용 시간대 계산"""
        # 운영 시간 (기본값 설정)
        if start_time is None:
            start_time = timedelta(hours=9)
        if end_time is None:
            end_time = timedelta(hours=18)
        
        # Batched 활동 시간
        busy_times = batched_blocks.get(applicant.id, []).copy()
        
        # 이미 스케줄된 Individual 활동 시간
        if applicant.id in schedule_by_applicant:
            for slot in schedule_by_applicant[applicant.id]:
                busy_times.append((slot.start_time, slot.end_time))
                
        # 병합 및 여유 시간 계산
        if not busy_times:
            return [(start_time, end_time)]
            
        busy_times = self._merge_time_blocks(busy_times)
        
        # 바쁜 시간의 역을 계산
        free_times = []
        current_start = start_time
        
        for busy_start, busy_end in busy_times:
            if current_start < busy_start:
                free_times.append((current_start, busy_start))
            current_start = max(current_start, busy_end)
            
        if current_start < end_time:
            free_times.append((current_start, end_time))
        
        return free_times
        
    def _merge_time_blocks(
        self, 
        blocks: List[Tuple[timedelta, timedelta]]
    ) -> List[Tuple[timedelta, timedelta]]:
        """시간 블록 병합"""
        if not blocks:
            return []
            
        sorted_blocks = sorted(blocks)
        merged = [sorted_blocks[0]]
        
        for current in sorted_blocks[1:]:
            last_start, last_end = merged[-1]
            current_start, current_end = current
            
            if current_start <= last_end:
                # 겹치면 병합
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                merged.append(current)
                
        return merged
        
    def _find_available_rooms(
        self,
        activity: Activity,
        rooms: List[Room],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]]
    ) -> List[Room]:
        """활동에 사용 가능한 방 찾기"""
        available = []
        
        for room in rooms:
            # 방 타입 확인
            if not any(rt in room.room_type for rt in activity.required_rooms):
                continue
                
            # 최소 하나의 시간대가 있는지 확인
            if room_availability.get(room.name):
                available.append(room)
                
        return available
        
    def _find_available_rooms_with_capacity(
        self,
        activity: Activity,
        rooms: List[Room],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        required_capacity: int
    ) -> List[Room]:
        """충분한 capacity를 가진 사용 가능한 방 찾기"""
        available = []
        
        for room in rooms:
            # 방 타입 확인
            if not any(rt in room.room_type for rt in activity.required_rooms):
                continue
                
            # Capacity 확인
            if room.capacity < required_capacity:
                continue
                
            # 최소 하나의 시간대가 있는지 확인
            if room_availability.get(room.name):
                available.append(room)
                
        return available
        
    def _update_availability(
        self,
        availability: List[Tuple[timedelta, timedelta]],
        start: timedelta,
        end: timedelta
    ) -> None:
        """가용 시간대에서 사용된 시간 제거"""
        new_availability = []
        
        for slot_start, slot_end in availability:
            if end <= slot_start or start >= slot_end:
                # 겹치지 않음
                new_availability.append((slot_start, slot_end))
            elif start <= slot_start and end >= slot_end:
                # 완전히 포함됨 - 제거
                pass
            elif start > slot_start and end < slot_end:
                # 중간 부분 - 분할
                new_availability.append((slot_start, start))
                new_availability.append((end, slot_end))
            elif start > slot_start:
                # 끝부분 겹침
                new_availability.append((slot_start, start))
            else:
                # 앞부분 겹침
                new_availability.append((end, slot_end))
                
        availability[:] = new_availability
        
    def _extract_cpsat_results(
        self,
        solver,
        intervals,
        presence_vars,
        room_vars,
        applicants: List[Applicant],
        activities: List[Activity],
        rooms: List[Room],
        date_str: str,
        start_time: timedelta
    ) -> IndividualScheduleResult:
        """🔍 개선된 CP-SAT 결과 추출 - 체류시간 최적화 결과 포함"""
        assignments = {}
        schedule_by_applicant = defaultdict(list)
        schedule_by_room = defaultdict(list)
        
        logger.info("📤 CP-SAT 최적화 결과 추출 중...")
        
        # 기준 시간 설정 (운영 시작 시간)
        base_time = start_time
        
        extracted_count = 0
        for (applicant_id, activity_name), interval in intervals.items():
            if solver.Value(presence_vars[(applicant_id, activity_name)]):
                start_min = solver.Value(interval.StartExpr())
                end_min = solver.Value(interval.EndExpr())
                
                # 방 찾기
                assigned_room = None
                for room in rooms:
                    key = (applicant_id, activity_name, room.name)
                    if key in room_vars and solver.Value(room_vars[key]):
                        assigned_room = room.name
                        break
                        
                if assigned_room:
                    # 분 단위를 실제 시간으로 변환
                    actual_start = base_time + timedelta(minutes=start_min)
                    actual_end = base_time + timedelta(minutes=end_min)
                    
                    time_slot = TimeSlot(
                        activity_name=activity_name,
                        start_time=actual_start,
                        end_time=actual_end,
                        room_name=assigned_room,
                        applicant_id=applicant_id
                    )
                    
                    key = f"{applicant_id}_{activity_name}"
                    assignments[key] = time_slot
                    schedule_by_applicant[applicant_id].append(time_slot)
                    schedule_by_room[assigned_room].append(time_slot)
                    
                    extracted_count += 1
                    logger.debug(f"  {applicant_id} {activity_name}: {actual_start} ~ {actual_end} ({assigned_room})")
                else:
                    logger.warning(f"⚠️ {applicant_id} {activity_name}: 방 배정 정보 누락")
        
        logger.info(f"✅ {extracted_count}개 활동 결과 추출 완료")
                    
        return IndividualScheduleResult(
            assignments=dict(assignments),
            schedule_by_applicant=dict(schedule_by_applicant),
            schedule_by_room=dict(schedule_by_room),
            success=True
        )

    def _optimize_activity_order(
        self,
        activities: List[Activity],
        precedence_rules: List[PrecedenceRule],
        applicants: List[Applicant]
    ) -> List[Activity]:
        """개선된 스케줄링 순서 결정"""
        # 활동 이름 -> Activity 매핑
        activity_map = {a.name: a for a in activities}
        activity_names = [a.name for a in activities]
        
        # ✨ 개선 1: precedence 체인 분석
        precedence_chains = self._analyze_precedence_chains(precedence_rules, activity_names)
        
        # ✨ 개선 2: 제약이 강한 활동(adjacent=True) 우선 처리
        adjacent_activities = set()
        for rule in precedence_rules:
            if rule.is_adjacent:
                adjacent_activities.add(rule.predecessor)
                adjacent_activities.add(rule.successor)
        
        # ✨ 개선 3: 순서 최적화
        ordered_names = []
        processed = set()
        
        # 1단계: precedence 체인이 있는 활동들을 체인 순서대로 처리
        for chain in precedence_chains:
            for activity_name in chain:
                if activity_name in activity_names and activity_name not in processed:
                    ordered_names.append(activity_name)
                    processed.add(activity_name)
        
        # 2단계: 남은 활동들 추가
        for name in activity_names:
            if name not in processed:
                ordered_names.append(name)
                processed.add(name)
        
        logger.info(f"최적화된 활동 순서: {ordered_names}")
        if precedence_chains:
            logger.info(f"Precedence 체인: {precedence_chains}")
        
        # Activity 객체 리스트로 변환
        return [activity_map[name] for name in ordered_names]
    
    def _analyze_precedence_chains(
        self, 
        precedence_rules: List[PrecedenceRule], 
        activity_names: List[str]
    ) -> List[List[str]]:
        """Precedence 규칙에서 체인 구조 분석"""
        # 의존성 그래프 구성
        dependencies = defaultdict(set)  # successor -> {predecessors}
        dependents = defaultdict(set)     # predecessor -> {successors}
        
        for rule in precedence_rules:
            if rule.predecessor in activity_names and rule.successor in activity_names:
                dependencies[rule.successor].add(rule.predecessor)
                dependents[rule.predecessor].add(rule.successor)
        
        # 체인 찾기
        chains = []
        visited = set()
        
        # 각 활동에서 시작하는 체인 찾기
        for activity in activity_names:
            if activity in visited:
                continue
                
            # 체인의 시작점 찾기 (predecessor가 없는 활동)
            if activity not in dependencies or not dependencies[activity]:
                chain = self._build_chain(activity, dependents, visited)
                if len(chain) > 1:  # 체인이 있는 경우만 추가
                    chains.append(chain)
        
        return chains
    
    def _build_chain(
        self, 
        start_activity: str, 
        dependents: Dict[str, set], 
        visited: set
    ) -> List[str]:
        """특정 활동에서 시작하는 체인 구축"""
        chain = []
        current = start_activity
        
        while current and current not in visited:
            chain.append(current)
            visited.add(current)
            
            # 다음 활동 찾기 (successor가 하나인 경우만)
            successors = dependents.get(current, set())
            if len(successors) == 1:
                current = list(successors)[0]
            else:
                break
                
        return chain
    
    def _get_group_common_free_times(
        self,
        group: List[Applicant],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        start_time: timedelta,
        end_time: timedelta
    ) -> List[Tuple[timedelta, timedelta]]:
        """그룹 내 모든 지원자의 공통 가용 시간 계산"""
        common_free_times = None
        
        for applicant in group:
            applicant_free_times = self._get_applicant_free_times(
                applicant, batched_blocks, schedule_by_applicant, start_time, end_time
            )
            
            if common_free_times is None:
                common_free_times = applicant_free_times
            else:
                # 교집합 계산
                new_common = []
                for common_slot in common_free_times:
                    for app_slot in applicant_free_times:
                        overlap_start = max(common_slot[0], app_slot[0])
                        overlap_end = min(common_slot[1], app_slot[1])
                        
                        if overlap_end > overlap_start:
                            new_common.append((overlap_start, overlap_end))
                            
                common_free_times = new_common
        
        return common_free_times or []
    
    def _schedule_activities_basic(
        self,
        activities_list: List[Activity],
        applicants: List[Applicant],
        rooms: List[Room],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        precedence_rules: List[PrecedenceRule],
        start_time: timedelta,
        end_time: timedelta,
        global_gap_min: int,
        all_activities: List[Activity] = None
    ) -> bool:
        """기본 방식으로 활동들 스케줄링"""
        for activity in activities_list:
            success = self._schedule_single_activity(
                activity, applicants, rooms, room_availability,
                batched_blocks, assignments, schedule_by_applicant,
                schedule_by_room, date_str, precedence_rules,
                start_time, end_time, global_gap_min, all_activities
            )
            if not success:
                return False
        return True
    
    def _schedule_single_activity(
        self,
        activity: Activity,
        applicants: List[Applicant],
        rooms: List[Room],
        room_availability: Dict[str, List[Tuple[timedelta, timedelta]]],
        batched_blocks: Dict[str, List[Tuple[timedelta, timedelta]]],
        assignments: Dict[str, TimeSlot],
        schedule_by_applicant: Dict[str, List[TimeSlot]],
        schedule_by_room: Dict[str, List[TimeSlot]],
        date_str: str,
        precedence_rules: List[PrecedenceRule],
        start_time: timedelta,
        end_time: timedelta,
        global_gap_min: int,
        activities: List[Activity] = None
    ) -> bool:
        """단일 활동 스케줄링"""
        if activity.mode == ActivityMode.INDIVIDUAL:
            return self._schedule_individual_activity(
                activity, applicants, rooms, room_availability,
                batched_blocks, assignments, schedule_by_applicant,
                schedule_by_room, date_str, precedence_rules,
                start_time, end_time, global_gap_min, activities
            )
        else:  # PARALLEL
            return self._schedule_parallel_activity(
                activity, applicants, rooms, room_availability,
                batched_blocks, assignments, schedule_by_applicant,
                schedule_by_room, date_str, start_time, end_time,
                precedence_rules, global_gap_min, activities
            )
    
    def _get_successor_room_count(
        self, 
        activity_name: str, 
        precedence_rules: List[PrecedenceRule], 
        rooms: List[Room],
        activities: List[Activity] = None
    ) -> int:
        """후속 활동의 방 개수 계산"""
        for rule in precedence_rules:
            if rule.predecessor == activity_name and rule.is_adjacent:
                successor_name = rule.successor
                # 후속 활동의 방 타입을 activities에서 찾기
                successor_room_type = None
                if activities:
                    for act in activities:
                        if act.name == successor_name:
                            successor_room_type = act.room_type
                            break
                
                if successor_room_type:
                    successor_rooms = [r for r in rooms if r.room_type == successor_room_type]
                    return len(successor_rooms)
        
        return float('inf')  # 후속 활동이 없으면 제한 없음 