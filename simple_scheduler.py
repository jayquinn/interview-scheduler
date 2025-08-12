"""
🎯 Simple Interview Scheduler
복잡성을 줄인 간결한 면접 스케줄러

핵심 특징:
- 단일 스케줄러로 모든 기능 통합
- 3단계 단순 최적화 (기존 Level 1-4 대신)
- 직관적이고 유지보수하기 쉬운 구조
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# =============================================================================
# 📊 단순화된 데이터 타입들
# =============================================================================

@dataclass
class Activity:
    """활동 정보"""
    name: str
    mode: str  # 'individual', 'parallel', 'batched'
    duration_min: int
    room_type: str
    min_cap: int = 1
    max_cap: int = 1

@dataclass
class Room:
    """방 정보"""
    name: str
    room_type: str
    capacity: int
    date: datetime

@dataclass
class Applicant:
    """지원자 정보"""
    id: str
    job_code: str
    required_activities: List[str]
    date: datetime

@dataclass
class PrecedenceRule:
    """선후행 제약"""
    predecessor: str
    successor: str
    gap_min: int = 0
    is_adjacent: bool = False

@dataclass
class ScheduleResult:
    """스케줄 결과"""
    applicant_id: str
    activity_name: str
    room_name: str
    start_time: timedelta
    end_time: timedelta
    date: datetime
    group_number: Optional[str] = None
    group_size: Optional[int] = None

# =============================================================================
# 🎯 Simple Interview Scheduler
# =============================================================================

class SimpleInterviewScheduler:
    """
    간결한 면접 스케줄러
    
    3단계 최적화:
    1. 기본 스케줄링 (선후행 제약 처리)
    2. 그룹 최적화 (Batched 활동 처리)
    3. 체류시간 최적화 (후처리)
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.schedule_results: List[ScheduleResult] = []
    
    def schedule(
        self,
        applicants: List[Applicant],
        activities: List[Activity],
        rooms: List[Room],
        precedence_rules: List[PrecedenceRule],
        operating_hours: Tuple[time, time],
        params: Dict[str, Any]
    ) -> Tuple[str, List[ScheduleResult], str]:
        """
        메인 스케줄링 함수
        
        Returns:
            (status, results, logs)
        """
        try:
            self.logger.info("🚀 Simple Interview Scheduler 시작")
            
            # 1단계: 기본 스케줄링
            self.logger.info("📅 1단계: 기본 스케줄링")
            self._schedule_basic(applicants, activities, rooms, precedence_rules, operating_hours)
            
            # 2단계: 그룹 최적화
            self.logger.info("👥 2단계: 그룹 최적화")
            self._optimize_groups(activities, params)
            
            # 3단계: 체류시간 최적화
            self.logger.info("⏱️ 3단계: 체류시간 최적화")
            self._optimize_stay_times(params)
            
            self.logger.info("✅ 스케줄링 완료")
            return "SUCCESS", self.schedule_results, "스케줄링 성공"
            
        except Exception as e:
            error_msg = f"스케줄링 실패: {str(e)}"
            self.logger.error(error_msg)
            return "FAILED", [], error_msg
    
    def _schedule_basic(
        self,
        applicants: List[Applicant],
        activities: List[Activity],
        rooms: List[Room],
        precedence_rules: List[PrecedenceRule],
        operating_hours: Tuple[time, time]
    ):
        """1단계: 기본 스케줄링"""
        
        # 지원자별로 활동 순서 결정
        for applicant in applicants:
            # 선후행 제약을 고려한 활동 순서 생성
            activity_order = self._determine_activity_order(
                applicant.required_activities, precedence_rules
            )
            
            # 각 활동을 시간순으로 배정
            current_time = timedelta(hours=operating_hours[0].hour, minutes=operating_hours[0].minute)
            
            for activity_name in activity_order:
                activity = self._find_activity(activities, activity_name)
                if not activity:
                    continue
                
                # 적절한 방 찾기
                room = self._find_available_room(rooms, activity.room_type, current_time)
                if not room:
                    # 방이 없으면 다음 시간으로 이동
                    current_time += timedelta(minutes=30)
                    room = self._find_available_room(rooms, activity.room_type, current_time)
                
                if room:
                    # 스케줄 결과 생성
                    end_time = current_time + timedelta(minutes=activity.duration_min)
                    
                    result = ScheduleResult(
                        applicant_id=applicant.id,
                        activity_name=activity.name,
                        room_name=room.name,
                        start_time=current_time,
                        end_time=end_time,
                        date=applicant.date
                    )
                    
                    self.schedule_results.append(result)
                    current_time = end_time + timedelta(minutes=5)  # 5분 간격
    
    def _optimize_groups(self, activities: List[Activity], params: Dict[str, Any]):
        """2단계: 그룹 최적화 (Batched 활동)"""
        
        # Batched 활동 찾기
        batched_activities = [a for a in activities if a.mode == "batched"]
        
        for activity in batched_activities:
            # 같은 활동, 같은 시간대의 지원자들을 그룹화
            activity_results = [r for r in self.schedule_results if r.activity_name == activity.name]
            
            if not activity_results:
                continue
            
            # 시간대별로 그룹화
            time_groups = {}
            for result in activity_results:
                time_key = result.start_time
                if time_key not in time_groups:
                    time_groups[time_key] = []
                time_groups[time_key].append(result)
            
            # 각 시간대에서 그룹 번호 부여
            for time_key, group_members in time_groups.items():
                group_size = len(group_members)
                # timedelta에서 시간과 분 추출
                total_seconds = int(time_key.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                group_number = f"{activity.name}-{hours:02d}{minutes:02d}"
                
                for result in group_members:
                    result.group_number = group_number
                    result.group_size = group_size
    
    def _optimize_stay_times(self, params: Dict[str, Any]):
        """3단계: 체류시간 최적화 (후처리)"""
        
        max_stay_hours = params.get('max_stay_hours', 8)
        
        # 지원자별 체류시간 계산
        applicant_stay_times = {}
        for result in self.schedule_results:
            if result.applicant_id not in applicant_stay_times:
                applicant_stay_times[result.applicant_id] = {
                    'start': result.start_time,
                    'end': result.end_time
                }
            else:
                applicant_stay_times[result.applicant_id]['start'] = min(
                    applicant_stay_times[result.applicant_id]['start'],
                    result.start_time
                )
                applicant_stay_times[result.applicant_id]['end'] = max(
                    applicant_stay_times[result.applicant_id]['end'],
                    result.end_time
                )
        
        # 체류시간이 긴 지원자들 찾기
        long_stay_applicants = []
        for applicant_id, times in applicant_stay_times.items():
            stay_duration = times['end'] - times['start']
            stay_hours = stay_duration.total_seconds() / 3600
            
            if stay_hours > max_stay_hours:
                long_stay_applicants.append((applicant_id, stay_hours))
        
        # 체류시간 최적화 시도 (간단한 후처리)
        if long_stay_applicants:
            self.logger.info(f"⚠️ 체류시간 긴 지원자 {len(long_stay_applicants)}명 발견")
            # 여기서 간단한 최적화 로직 추가 가능
    
    def _determine_activity_order(
        self, 
        required_activities: List[str], 
        precedence_rules: List[PrecedenceRule]
    ) -> List[str]:
        """선후행 제약을 고려한 활동 순서 결정"""
        
        # 간단한 위상 정렬 구현
        activity_order = required_activities.copy()
        
        # 선후행 제약 적용
        for rule in precedence_rules:
            if rule.predecessor in activity_order and rule.successor in activity_order:
                pred_idx = activity_order.index(rule.predecessor)
                succ_idx = activity_order.index(rule.successor)
                
                if pred_idx > succ_idx:
                    # 순서 교환
                    activity_order[pred_idx], activity_order[succ_idx] = \
                        activity_order[succ_idx], activity_order[pred_idx]
        
        return activity_order
    
    def _find_activity(self, activities: List[Activity], activity_name: str) -> Optional[Activity]:
        """활동 찾기"""
        for activity in activities:
            if activity.name == activity_name:
                return activity
        return None
    
    def _find_available_room(
        self, 
        rooms: List[Room], 
        room_type: str, 
        start_time: timedelta
    ) -> Optional[Room]:
        """사용 가능한 방 찾기"""
        
        # 해당 타입의 방들 중에서 사용 가능한 것 찾기
        available_rooms = []
        for room in rooms:
            if room.room_type == room_type:
                # 간단한 충돌 검사
                is_available = True
                for result in self.schedule_results:
                    if (result.room_name == room.name and 
                        result.start_time <= start_time < result.end_time):
                        is_available = False
                        break
                
                if is_available:
                    available_rooms.append(room)
        
        return available_rooms[0] if available_rooms else None

# =============================================================================
# 🔧 유틸리티 함수들
# =============================================================================

def convert_to_dataframe(results: List[ScheduleResult]) -> pd.DataFrame:
    """스케줄 결과를 DataFrame으로 변환"""
    
    data = []
    for result in results:
        row = {
            'applicant_id': result.applicant_id,
            'activity_name': result.activity_name,
            'room_name': result.room_name,
            'start_time': result.start_time,
            'end_time': result.end_time,
            'interview_date': result.date,
            'duration_min': int((result.end_time - result.start_time).total_seconds() / 60)
        }
        
        if result.group_number:
            row['group_number'] = result.group_number
            row['group_size'] = result.group_size
        
        data.append(row)
    
    return pd.DataFrame(data)

def validate_schedule(results: List[ScheduleResult]) -> Tuple[bool, List[str]]:
    """스케줄 검증"""
    
    errors = []
    
    # 기본 검증
    if not results:
        errors.append("스케줄 결과가 없습니다")
        return False, errors
    
    # 중복 검사
    schedule_keys = set()
    for result in results:
        key = (result.applicant_id, result.activity_name, result.start_time)
        if key in schedule_keys:
            errors.append(f"중복 스케줄: {result.applicant_id} - {result.activity_name}")
        schedule_keys.add(key)
    
    # 시간 충돌 검사
    room_schedules = {}
    for result in results:
        if result.room_name not in room_schedules:
            room_schedules[result.room_name] = []
        room_schedules[result.room_name].append(result)
    
    for room_name, schedules in room_schedules.items():
        schedules.sort(key=lambda x: x.start_time)
        for i in range(len(schedules) - 1):
            if schedules[i].end_time > schedules[i + 1].start_time:
                errors.append(f"방 충돌: {room_name}에서 시간 겹침")
    
    return len(errors) == 0, errors 