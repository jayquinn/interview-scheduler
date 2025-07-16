"""
Level 1: 그룹 구성 최적화
Batched 활동을 위한 그룹을 구성하고 필요시 더미 지원자를 추가
"""
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import logging
import time

def parse_job_code(member_id: str) -> str:
    """ID에서 직무코드 추출 (예: DUMMY_JOB01_001 → JOB01)"""
    parts = member_id.split("_")
    for part in parts:
        if part.startswith("JOB"):
            return part
    return ""

from .types import (
    Applicant, Group, Activity, ActivityMode, Level1Result,
    calculate_group_count
)


class GroupOptimizer:
    """그룹 구성을 최적화하는 클래스"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.dummy_counter = 0
        
    def optimize(
        self,
        applicants: List[Applicant],
        activities: List[Activity],
        time_limit: float = 30.0,
        dummy_hint: int = 0
    ) -> Optional[Level1Result]:
        """
        최적 그룹 구성을 찾습니다.
        
        Args:
            applicants: 지원자 리스트
            activities: 활동 리스트
            time_limit: 시간 제한 (초)
            
        Returns:
            Level1Result 또는 None (실패시)
        """
        self.logger.info(f"그룹 최적화 시작: {len(applicants)}명 지원자")
        
        # Batched 활동만 필터링
        batched_activities = [
            act for act in activities
            if act.mode == ActivityMode.BATCHED
        ]
        
        if not batched_activities:
            # Batched 활동이 없으면 그룹 구성 불필요
            return Level1Result(
                groups={},
                applicants=applicants,
                dummy_count=0,
                group_count=0
            )
        
        # 직무별로 지원자 분류
        applicants_by_job = defaultdict(list)
        for applicant in applicants:
            applicants_by_job[applicant.job_code].append(applicant)
        
        # 각 활동별로 그룹 구성
        all_groups = {}
        total_dummy_count = 0
        
        # dummy_hint가 있으면 각 활동/직무에 균등 분배
        activities_jobs = []
        for activity in batched_activities:
            for job_code, job_applicants in applicants_by_job.items():
                activity_applicants = [
                    app for app in job_applicants
                    if activity.name in app.activities
                ]
                if activity_applicants:
                    activities_jobs.append((activity, job_code, activity_applicants))
        
        extra_dummy_per_group = 0
        if dummy_hint > 0 and activities_jobs:
            extra_dummy_per_group = max(1, dummy_hint // len(activities_jobs))
        
        for activity in batched_activities:
            activity_groups = []
            
            # 각 직무별로 그룹 생성
            for job_code, job_applicants in applicants_by_job.items():
                # 해당 직무가 이 활동을 수행하는지 확인
                activity_applicants = [
                    app for app in job_applicants
                    if activity.name in app.activities
                ]
                
                if not activity_applicants:
                    continue
                
                # 그룹 구성 (extra dummy 추가)
                groups, dummy_count = self._create_groups_for_job(
                    activity_applicants,
                    activity.name,
                    job_code,
                    activity.min_capacity,
                    activity.max_capacity,
                    extra_dummy=extra_dummy_per_group
                )
                
                activity_groups.extend(groups)
                total_dummy_count += dummy_count
            
            if activity_groups:
                all_groups[activity.name] = activity_groups
        
        # 더미 지원자를 포함한 전체 지원자 리스트 생성
        all_applicants = applicants.copy()
        
        # 생성된 그룹에서 더미 지원자 추출
        for activity_groups in all_groups.values():
            for group in activity_groups:
                # 더미 멤버만 추출
                dummy_members = [
                    mid for mid in group.members
                    if mid.startswith("DUMMY_")
                ]
                
                # 더미 지원자 객체 생성
                for dummy_id in dummy_members:
                    # 이미 추가되지 않았다면 추가
                    if not any(app.id == dummy_id for app in all_applicants):
                        # 더미 지원자의 직무와 활동 추출
                        parts = dummy_id.split("_")
                        dummy_job = parts[1] if len(parts) > 1 else group.job_code
                        
                        # 해당 직무의 활동 목록 가져오기
                        job_activities = []
                        for app in applicants:
                            if app.job_code == dummy_job:
                                job_activities = app.activities
                                break
                        
                        dummy = Applicant(
                            id=dummy_id,
                            job_code=dummy_job,
                            activities=job_activities,
                            is_dummy=True
                        )
                        all_applicants.append(dummy)
        
        total_group_count = sum(len(groups) for groups in all_groups.values())
        
        self.logger.info(
            f"그룹 최적화 완료: {total_group_count}개 그룹, "
            f"{total_dummy_count}명 더미"
        )
        
        return Level1Result(
            groups=all_groups,
            applicants=all_applicants,
            dummy_count=total_dummy_count,
            group_count=total_group_count
        )
    
    def _classify_by_job(self, applicants: List[Applicant]) -> Dict[str, List[Applicant]]:
        """직무별로 지원자 분류"""
        classified = defaultdict(list)
        for applicant in applicants:
            classified[applicant.job_code].append(applicant)
        return dict(classified)
    
    def _create_job_groups(
        self,
        job_code: str,
        job_applicants: List[Applicant],
        min_capacity: int,
        max_capacity: int
    ) -> Tuple[List[Group], List[Applicant]]:
        """
        직무별 그룹 구성 (활동과 무관하게)
        
        Returns:
            (그룹 리스트, 더미 지원자 리스트)
        """
        # 그룹 수 최적화
        total_count = len(job_applicants)
        group_count, dummy_count = calculate_group_count(
            total_count,
            min_capacity,
            max_capacity
        )
        
        self.logger.debug(
            f"{job_code}: {total_count}명 → {group_count}개 그룹, {dummy_count}명 더미"
        )
        
        # 더미 지원자 생성
        dummy_applicants = []
        if dummy_count > 0:
            # 이 직무의 지원자들이 수행하는 모든 활동
            all_activities = set()
            for app in job_applicants:
                all_activities.update(app.activities)
            
            for i in range(dummy_count):
                self.dummy_counter += 1
                dummy = Applicant.create_dummy(
                    job_code,
                    list(all_activities),
                    self.dummy_counter
                )
                dummy_applicants.append(dummy)
        
        # 전체 멤버 (실제 + 더미)
        all_members = job_applicants + dummy_applicants
        
        # 그룹 분배
        groups = []
        members_per_group = len(all_members) // group_count
        extra_members = len(all_members) % group_count
        
        current_idx = 0
        for i in range(group_count):
            # 이 그룹의 크기
            size = members_per_group + (1 if i < extra_members else 0)
            
            # 멤버 할당
            group_members = all_members[current_idx:current_idx + size]
            current_idx += size
            
            # 그룹 생성 (활동명 없이)
            group = Group(
                id=f"G_{job_code}_{i+1:03d}",
                activity="",  # 나중에 채워짐
                job_code=job_code,
                members=[m.id for m in group_members],
                size=len(group_members)
            )
            groups.append(group)
        
        return groups, dummy_applicants
    
    def _create_groups_for_activity(
        self,
        activity_name: str,
        activity: Activity,
        applicants_by_job: Dict[str, List[Applicant]],
        remaining_time: float
    ) -> Tuple[List[Group], List[Applicant]]:
        """
        특정 활동에 대한 그룹 구성
        
        Returns:
            (그룹 리스트, 더미 지원자 리스트)
        """
        all_groups = []
        all_dummy_applicants = []
        
        # 각 직무별로 그룹 구성
        for job_code, job_applicants in applicants_by_job.items():
            # 해당 활동을 수행하는 지원자만 필터링
            relevant_applicants = [
                app for app in job_applicants
                if activity_name in app.activities
            ]
            
            if not relevant_applicants:
                continue
            
            # 최적 그룹 수 계산
            total_count = len(relevant_applicants)
            group_count, dummy_count = calculate_group_count(
                total_count,
                activity.min_capacity,
                activity.max_capacity
            )
            
            self.logger.debug(
                f"{job_code} - {activity_name}: "
                f"{total_count}명 → {group_count}개 그룹, {dummy_count}명 더미"
            )
            
            # 더미 지원자 생성 - 모든 batched 활동을 수행하도록
            # (precedence가 작동하려면 같은 그룹이 여러 활동을 해야 함)
            dummy_applicants = []
            for i in range(dummy_count):
                self.dummy_counter += 1
                # 이 직무의 다른 지원자들이 하는 모든 활동을 더미도 수행
                all_activities = set()
                for app in job_applicants:
                    all_activities.update(app.activities)
                
                dummy = Applicant.create_dummy(
                    job_code,
                    list(all_activities),  # 모든 활동 수행
                    self.dummy_counter
                )
                dummy_applicants.append(dummy)
            
            # 전체 지원자 리스트 (실제 + 더미)
            all_members = relevant_applicants + dummy_applicants
            
            # 그룹 생성 - 활동명을 제외한 ID 사용
            groups = self._distribute_into_groups(
                all_members,
                group_count,
                activity_name,
                job_code
            )
            
            all_groups.extend(groups)
            all_dummy_applicants.extend(dummy_applicants)
            
            # 시간 체크
            if remaining_time <= 0:
                self.logger.warning("시간 제한으로 그룹 구성 중단")
                break
        
        return all_groups, all_dummy_applicants
    
    def _distribute_into_groups(
        self,
        applicants: List[Applicant],
        group_count: int,
        activity_name: str,
        job_code: str
    ) -> List[Group]:
        """지원자들을 그룹으로 분배"""
        if group_count == 0:
            return []
        
        groups = []
        members_per_group = len(applicants) // group_count
        extra_members = len(applicants) % group_count
        
        current_idx = 0
        for i in range(group_count):
            # 이 그룹의 크기 결정
            size = members_per_group + (1 if i < extra_members else 0)
            
            # 멤버 할당
            group_members = applicants[current_idx:current_idx + size]
            current_idx += size
            
            # 그룹 생성 - 활동명을 제외하여 같은 멤버는 같은 그룹 ID 유지
            group = Group(
                id=f"G_{job_code}_{i+1:03d}",  # 활동명 제외
                activity=activity_name,
                job_code=job_code,
                members=[m.id for m in group_members],
                size=len(group_members)  # size 명시적으로 전달
            )
            groups.append(group)
        
        return groups
    
    def validate_groups(
        self,
        groups: Dict[str, List[Group]],
        activities: Dict[str, Activity]
    ) -> List[str]:
        """
        생성된 그룹 검증
        
        Returns:
            오류 메시지 리스트
        """
        errors = []
        
        for activity_name, activity_groups in groups.items():
            if activity_name not in activities:
                errors.append(f"알 수 없는 활동: {activity_name}")
                continue
            
            activity = activities[activity_name]
            
            for group in activity_groups:
                # 그룹 크기 검증
                if group.size < activity.min_capacity:
                    errors.append(
                        f"{group.id}: 최소 인원({activity.min_capacity}) 미달"
                    )
                elif group.size > activity.max_capacity:
                    errors.append(
                        f"{group.id}: 최대 인원({activity.max_capacity}) 초과"
                    )
                
                # 동일 직무 검증
                job_codes = set()
                for member_id in group.members:
                    job_code = parse_job_code(member_id)
                    job_codes.add(job_code)
                
                if len(job_codes) > 1:
                    errors.append(
                        f"{group.id}: 서로 다른 직무 혼재 {job_codes}"
                    )
        
        return errors
    
    def _create_groups_for_job(
        self,
        applicants: List[Applicant],
        activity_name: str,
        job_code: str,
        min_capacity: int,
        max_capacity: int,
        extra_dummy: int = 0
    ) -> Tuple[List[Group], int]:
        """
        특정 직무와 활동에 대한 그룹 생성
        
        Returns:
            (그룹 리스트, 더미 수)
        """
        total = len(applicants)
        
        if total == 0:
            return [], 0
            
        # 최적 그룹 수와 더미 수 계산
        group_count, base_dummy_count = calculate_group_count(
            total, min_capacity, max_capacity
        )
        
        # extra_dummy 추가
        dummy_count = base_dummy_count + extra_dummy
        
        # extra_dummy 추가 후 그룹 수 재계산 필요시
        if dummy_count > base_dummy_count:
            total_with_extra = total + dummy_count
            group_count = (total_with_extra + max_capacity - 1) // max_capacity
        
        self.logger.info(
            f"{job_code}/{activity_name}: {total}명 → "
            f"{dummy_count}명 더미 추가 (기본 {base_dummy_count} + 추가 {extra_dummy}) → {group_count}개 그룹"
        )
        
        # 더미 지원자 ID 생성
        all_member_ids = [app.id for app in applicants]
        for i in range(dummy_count):
            dummy_id = f"DUMMY_{job_code}_{str(i+1).zfill(3)}"
            all_member_ids.append(dummy_id)
        
        # 그룹 구성
        total_with_dummy = total + dummy_count
        group_size = total_with_dummy // group_count
        
        groups = []
        for i in range(group_count):
            start_idx = i * group_size
            end_idx = start_idx + group_size
            
            # 마지막 그룹은 남은 인원 모두 포함
            if i == group_count - 1:
                end_idx = total_with_dummy
                
            members = all_member_ids[start_idx:end_idx]
            
            group = Group(
                id=f"{job_code}_{activity_name}_G{i+1}",
                activity=activity_name,
                job_code=job_code,
                members=members,
                size=len(members)
            )
            groups.append(group)
        
        return groups, dummy_count 