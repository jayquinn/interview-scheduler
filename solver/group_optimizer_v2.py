"""
개선된 그룹 최적화: 같은 그룹이 여러 batched 활동 수행
"""
import logging
import time as time_module
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

from .types import (
    Applicant, Activity, Group, ActivityMode, Level1Result,
    calculate_group_count
)


class GroupOptimizerV2:
    """
    개선된 그룹 최적화기
    - 같은 그룹이 모든 batched 활동을 수행
    - Precedence 제약이 제대로 작동하도록 보장
    """
    
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
        Level 1: 그룹 구성 최적화 (개선된 버전)
        
        전략:
        1. 직무별로 분리
        2. 각 직무 내에서 공통 그룹을 구성 (모든 batched 활동 공유)
        3. 그룹 수 최소화 우선, 동일 그룹 수면 더 큰 균등 크기 선호
        """
        self.logger.info(f"그룹 최적화 시작 (V2): {len(applicants)}명 지원자")
        start_time = time_module.time()
        
        # Batched 활동만 필터링
        batched_activities = [
            a for a in activities 
            if a.mode == ActivityMode.BATCHED
        ]
        
        if not batched_activities:
            # Batched 활동이 없으면 빈 그룹으로 반환
            return Level1Result(
                groups={},
                applicants=applicants,
                dummy_count=0,
                group_count=0
            )
        
        # 직무별로 지원자 분류
        applicants_by_job = self._classify_by_job(applicants)
        
        # 각 직무별로 공통 그룹 구성 (모든 batched 활동에서 재사용)
        job_groups = {}  # job_code -> List[Group]
        total_dummy_count = 0
        
        for job_code, job_applicants in applicants_by_job.items():
            # 이 직무의 지원자들이 수행하는 batched 활동들
            job_batched_activities = []
            for activity in batched_activities:
                # 이 직무에서 이 활동을 수행하는 지원자가 있는지 확인
                has_activity = any(activity.name in app.required_activities for app in job_applicants)
                if has_activity:
                    job_batched_activities.append(activity)
            
            if not job_batched_activities:
                continue
                
            # 가장 제한적인 그룹 크기 찾기 (모든 활동에서 사용 가능한 크기)
            min_capacity = max(act.min_capacity for act in job_batched_activities)
            max_capacity = min(act.max_capacity for act in job_batched_activities)
            
            self.logger.info(
                f"{job_code}: {len(job_applicants)}명, "
                f"그룹 크기 {min_capacity}~{max_capacity} "
                f"(활동: {[a.name for a in job_batched_activities]})"
            )
            
            # 공통 그룹 생성
            groups, dummy_count = self._create_common_groups(
                job_applicants,
                job_code,
                min_capacity,
                max_capacity,
                job_batched_activities
            )
            
            job_groups[job_code] = groups
            total_dummy_count += dummy_count
        
        # 활동별로 그룹 할당 (같은 그룹이 모든 활동 수행)
        all_groups = {}
        for activity in batched_activities:
            activity_groups = []
            
            for job_code, groups in job_groups.items():
                # 이 직무에서 이 활동을 수행하는지 확인
                job_applicants = applicants_by_job[job_code]
                has_activity = any(activity.name in app.required_activities for app in job_applicants)
                
                if has_activity:
                                         # 그룹 ID를 동일하게 유지 (precedence를 위해)
                     for group in groups:
                         activity_group = Group(
                             id=f"{job_code}_{group.id}",  # 활동명 제외하고 동일한 ID 유지
                             activity_name=activity.name,
                             job_code=job_code,
                             applicants=group.applicants.copy(),  # 동일한 멤버
                             size=group.size
                         )
                         activity_groups.append(activity_group)
            
            if activity_groups:
                all_groups[activity.name] = activity_groups
        
        # 더미 지원자를 포함한 전체 지원자 리스트 생성
        all_applicants = applicants.copy()
        
        # 생성된 그룹에서 더미 지원자 추출 (중복 제거)
        added_dummies = set()
        for activity_groups in all_groups.values():
            for group in activity_groups:
                # 더미 멤버만 추출 (dummy_ids 속성 사용)
                dummy_members = []
                if hasattr(group, 'dummy_ids'):
                    dummy_members = [
                        mid for mid in group.dummy_ids
                        if mid not in added_dummies
                    ]
                
                # 더미 지원자 객체 생성
                for dummy_id in dummy_members:
                    added_dummies.add(dummy_id)
                    
                    # 더미 지원자의 직무와 활동 추출
                    parts = dummy_id.split("_")
                    dummy_job = parts[1] if len(parts) > 1 else group.job_code
                    
                    # 해당 직무의 활동 목록 가져오기
                    job_activities = []
                    for app in applicants:
                        if app.job_code == dummy_job:
                            job_activities = app.required_activities
                            break
                    
                    dummy = Applicant(
                        id=dummy_id,
                        job_code=dummy_job,
                        required_activities=job_activities,
                        is_dummy=True
                    )
                    all_applicants.append(dummy)
        
        total_group_count = sum(len(groups) for groups in all_groups.values())
        
        self.logger.info(
            f"그룹 최적화 완료 (V2): {total_group_count}개 그룹, "
            f"{total_dummy_count}명 더미"
        )
        
        return Level1Result(
            groups=all_groups,
            applicants=all_applicants,
            dummy_count=total_dummy_count
        )
    
    def _classify_by_job(self, applicants: List[Applicant]) -> Dict[str, List[Applicant]]:
        """직무별로 지원자 분류"""
        classified = defaultdict(list)
        for applicant in applicants:
            classified[applicant.job_code].append(applicant)
        return dict(classified)
    
    def _create_common_groups(
        self,
        job_applicants: List[Applicant],
        job_code: str,
        min_capacity: int,
        max_capacity: int,
        batched_activities: List[Activity]
    ) -> Tuple[List[Group], int]:
        """
        직무별 공통 그룹 구성 (모든 batched 활동에서 재사용)
        
        Returns:
            (그룹 리스트, 더미 지원자 수)
        """
        # 그룹 수 최적화
        total_count = len(job_applicants)
        group_count, dummy_count = calculate_group_count(
            total_count,
            min_capacity,
            max_capacity
        )
        
        self.logger.info(
            f"{job_code}: {total_count}명 → {dummy_count}명 더미 추가 "
            f"→ {total_count + dummy_count}명 → {group_count}개 그룹"
        )
        
        # 더미 지원자 ID 생성 (실제 객체는 나중에)
        dummy_ids = []
        if dummy_count > 0:
            for i in range(dummy_count):
                self.dummy_counter += 1
                dummy_id = f"DUMMY_{job_code}_{self.dummy_counter:03d}"
                dummy_ids.append(dummy_id)
        
        # 전체 멤버 ID (실제 + 더미)
        all_member_ids = [app.id for app in job_applicants] + dummy_ids
        
        # 그룹 분배
        groups = []
        members_per_group = len(all_member_ids) // group_count
        extra_members = len(all_member_ids) % group_count
        
        current_idx = 0
        for i in range(group_count):
            # 이 그룹의 크기
            size = members_per_group + (1 if i < extra_members else 0)
            
            # 멤버 할당
            group_member_ids = all_member_ids[current_idx:current_idx + size]
            current_idx += size
            
            # 실제 Applicant 객체들 찾기
            group_applicants = []
            for member_id in group_member_ids:
                if member_id.startswith("DUMMY_"):
                    # 더미 지원자는 나중에 생성되므로 일단 빈 리스트
                    continue
                else:
                    # 실제 지원자 찾기
                    for app in job_applicants:
                        if app.id == member_id:
                            group_applicants.append(app)
                            break
            
            # 그룹 생성 (활동명 없이, 나중에 각 활동별로 복사됨)
            group = Group(
                id=f"G{i+1:03d}",  # 단순한 ID
                activity_name="COMMON",  # 공통 그룹 표시
                job_code=job_code,
                applicants=group_applicants,
                size=len(group_member_ids)  # 더미 포함 전체 크기
            )
            # 더미 ID들을 따로 저장 (나중에 더미 지원자 생성용)
            group.dummy_ids = [mid for mid in group_member_ids if mid.startswith("DUMMY_")]
            groups.append(group)
        
        return groups, dummy_count 