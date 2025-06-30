"""
면접 스케줄링 시스템의 타입 정의
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from datetime import datetime, time, timedelta
from enum import Enum
import pandas as pd


# Callback 타입
ProgressCallback = Callable[['ProgressInfo'], None]


@dataclass
class ProgressInfo:
    """진행 상황 정보"""
    stage: str
    progress: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# Enum 정의
class ActivityMode(Enum):
    """활동 모드"""
    INDIVIDUAL = "individual"
    PARALLEL = "parallel"
    BATCHED = "batched"


# ActivityType은 ActivityMode의 별칭으로 사용
ActivityType = ActivityMode


@dataclass
class Activity:
    """면접 활동 정의"""
    name: str
    mode: ActivityMode
    duration_min: int
    room_type: str
    required_rooms: List[str] = field(default_factory=list)
    min_capacity: int = 1
    max_capacity: int = 1
    
    @property
    def duration(self) -> timedelta:
        """duration_min을 timedelta로 변환"""
        return timedelta(minutes=self.duration_min)


@dataclass
class Room:
    """면접실 정의"""
    name: str
    room_type: str
    capacity: int
    
    def get_suffix(self) -> str:
        """방 이름에서 접미사 추출 (예: '토론면접실A' -> 'A')"""
        # 방 이름의 마지막 문자가 알파벳인 경우 접미사로 사용
        if self.name and len(self.name) > 0:
            last_char = self.name[-1]
            if last_char.isalpha():
                return last_char.upper()
        return 'A'  # 기본값


@dataclass
class Applicant:
    """지원자 정보"""
    id: str
    job_code: str
    required_activities: List[str] = field(default_factory=list)
    is_dummy: bool = False


@dataclass
class Group:
    """그룹 정보 (batched 활동용)"""
    id: str
    job_code: str
    applicants: List[Applicant]
    size: int
    activity_name: str


@dataclass
class TimeSlot:
    """시간 슬롯"""
    start_time: timedelta
    end_time: timedelta
    room_name: str
    activity_name: str
    applicant_id: Optional[str] = None
    group_id: Optional[str] = None


@dataclass
class ScheduleItem:
    """스케줄 항목"""
    applicant_id: str
    job_code: str
    activity_name: str
    room_name: str
    start_time: timedelta
    end_time: timedelta
    group_id: Optional[str] = None


@dataclass
class PrecedenceRule:
    """선후행 제약 규칙"""
    predecessor: str
    successor: str
    gap_min: int = 0
    is_adjacent: bool = False


@dataclass
class GroupAssignment:
    """그룹 배정 정보"""
    group: Group
    room: Room
    start_time: timedelta
    end_time: timedelta


@dataclass
class RoomAssignment:
    """방 배정 정보"""
    room: Room
    time_slots: List[TimeSlot] = field(default_factory=list)


@dataclass
class GroupScheduleResult:
    """그룹 스케줄링 결과"""
    activity_name: str
    assignments: List[GroupAssignment] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    # 누락된 속성들 추가
    schedule_by_applicant: Dict[str, List[TimeSlot]] = field(default_factory=dict)
    schedule_by_room: Dict[str, List[TimeSlot]] = field(default_factory=dict)


@dataclass
class IndividualScheduleResult:
    """개별 스케줄링 결과"""
    schedule: List[TimeSlot] = field(default_factory=list)
    unscheduled: List[Applicant] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    # 누락된 속성들 추가
    assignments: Dict[str, TimeSlot] = field(default_factory=dict)
    schedule_by_applicant: Dict[str, List[TimeSlot]] = field(default_factory=dict)
    schedule_by_room: Dict[str, List[TimeSlot]] = field(default_factory=dict)


@dataclass
class Level1Result:
    """Level 1 결과 (그룹 생성)"""
    groups: Dict[str, List[Group]] = field(default_factory=dict)
    applicants: List[Applicant] = field(default_factory=list)
    dummy_count: int = 0


@dataclass
class Level2Result:
    """Level 2 결과 (Batched 스케줄링)"""
    schedule: List[ScheduleItem] = field(default_factory=list)
    room_assignments: Dict[str, RoomAssignment] = field(default_factory=dict)
    group_results: List[GroupScheduleResult] = field(default_factory=list)


@dataclass
class Level3Result:
    """Level 3 결과 (Individual/Parallel 스케줄링)"""
    schedule: List[ScheduleItem] = field(default_factory=list)
    unscheduled: List[Applicant] = field(default_factory=list)


@dataclass
class SingleDateResult:
    """단일 날짜 스케줄링 결과"""
    date: datetime
    status: str  # "SUCCESS", "PARTIAL", "FAILED"
    schedule: List[ScheduleItem] = field(default_factory=list)
    total_applicants: int = 0
    scheduled_applicants: int = 0
    unscheduled_applicants: int = 0
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    # 백트래킹 정보
    backtrack_count: int = 0
    attempted_configs: List[dict] = field(default_factory=list)
    
    # 단계별 결과 (디버깅용)
    level1_result: Optional['Level1Result'] = None
    level2_result: Optional['Level2Result'] = None
    level3_result: Optional['Level3Result'] = None
    
    def to_dataframe(self) -> pd.DataFrame:
        """스케줄을 DataFrame으로 변환"""
        if not self.schedule:
            return pd.DataFrame()
        
        data = []
        for item in self.schedule:
            data.append({
                'applicant_id': item.applicant_id,
                'job_code': item.job_code,
                'activity_name': item.activity_name,
                'room_name': item.room_name,
                'start_time': item.start_time,
                'end_time': item.end_time,
                'group_id': item.group_id,
                'interview_date': self.date.date()
            })
        
        return pd.DataFrame(data)


@dataclass
class MultiDateResult:
    """멀티 날짜 스케줄링 결과"""
    status: str  # "SUCCESS", "PARTIAL", "FAILED"
    results: Dict[datetime, SingleDateResult] = field(default_factory=dict)
    total_applicants: int = 0
    scheduled_applicants: int = 0
    failed_dates: List[datetime] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """전체 스케줄을 DataFrame으로 변환"""
        all_dataframes = []
        
        for date, result in self.results.items():
            if result.status != "FAILED":
                df = result.to_dataframe()
                if not df.empty:
                    all_dataframes.append(df)
        
        if not all_dataframes:
            return pd.DataFrame()
        
        return pd.concat(all_dataframes, ignore_index=True)


@dataclass
class DatePlan:
    """날짜별 계획"""
    date: datetime
    jobs: Dict[str, int]  # {job_code: count}
    selected_activities: List[str]
    overrides: Optional[Dict] = None
    
    def get_total_applicants(self) -> int:
        """총 지원자 수 반환"""
        return sum(self.jobs.values())


@dataclass
class DateConfig:
    """날짜별 설정 (실행용)"""
    date: datetime
    jobs: Dict[str, int]
    activities: List[Activity]
    rooms: List[Room]
    operating_hours: Tuple[timedelta, timedelta]
    precedence_rules: List[PrecedenceRule] = field(default_factory=list)
    job_activity_matrix: Dict[Tuple[str, str], bool] = field(default_factory=dict)
    global_gap_min: int = 5


@dataclass
class GlobalConfig:
    """전역 설정"""
    operating_hours: Dict[str, Tuple[time, time]] = field(default_factory=dict)
    precedence_rules: List[PrecedenceRule] = field(default_factory=list)
    batched_group_sizes: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    room_settings: Dict[str, Dict] = field(default_factory=dict)
    time_settings: Dict[str, int] = field(default_factory=dict)
    global_gap_min: int = 5
    max_stay_hours: int = 8


@dataclass
class SchedulingContext:
    """스케줄링 컨텍스트"""
    progress_callback: Optional[ProgressCallback] = None
    time_limit_sec: float = 120.0
    debug: bool = False


# Utility functions
def calculate_group_count(
    total_count: int, 
    min_capacity: int, 
    max_capacity: int
) -> Tuple[int, int]:
    """
    그룹 수와 더미 지원자 수를 계산
    
    Args:
        total_count: 총 지원자 수
        min_capacity: 그룹 최소 인원
        max_capacity: 그룹 최대 인원
    
    Returns:
        (그룹 수, 더미 지원자 수)
    """
    if total_count <= 0:
        return 0, 0
    
    if min_capacity > max_capacity:
        raise ValueError(f"min_capacity({min_capacity}) > max_capacity({max_capacity})")
    
    # 그룹 구성이 불가능한 경우 검사
    if total_count < min_capacity:
        # 최소 그룹 크기보다 지원자가 적으면 그룹 구성 불가
        # 하지만 더미를 추가하여 1개 그룹 구성 시도
        dummies_needed = min_capacity - total_count
        return 1, dummies_needed
    
    # 최소 그룹 수
    min_groups = (total_count + max_capacity - 1) // max_capacity
    
    # 각 그룹 수별로 더미 지원자 수 계산
    best_groups = min_groups
    best_dummies = float('inf')
    
    # 최소 그룹 수부터 시작해서 가능한 그룹 수 탐색
    for group_count in range(min_groups, total_count // min_capacity + 1):
        # 각 그룹의 평균 크기
        avg_size = total_count / group_count
        
        # 모든 그룹이 min_capacity 이상이어야 함
        if avg_size < min_capacity:
            break
        
        # 필요한 총 인원 (그룹 크기는 min_capacity 이상)
        needed_total = group_count * min_capacity
        dummies_needed = max(0, needed_total - total_count)
        
        # 최대 용량 초과 확인
        max_total_capacity = group_count * max_capacity
        if total_count + dummies_needed > max_total_capacity:
            continue
        
        # 더 적은 더미가 필요한 경우 또는 같은 더미 수면 더 적은 그룹 수 선택
        if dummies_needed < best_dummies or (dummies_needed == best_dummies and group_count < best_groups):
            best_groups = group_count
            best_dummies = dummies_needed
    
    # 여전히 infinity인 경우 (그룹 구성 불가)
    if best_dummies == float('inf'):
        # 최후의 수단: 1개 그룹으로 강제 구성
        best_groups = 1
        best_dummies = min_capacity - total_count
    
    return best_groups, int(best_dummies)