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
        """
        self.logger.info(f"[진단] 그룹 최적화 시작 (V2): {len(applicants)}명 지원자, 활동: {[a.name for a in activities]}")
        start_time = time_module.time()
        # Batched 활동만 필터링
        batched_activities = [
            a for a in activities 
            if a.mode == ActivityMode.BATCHED
        ]
        self.logger.info(f"[진단] Batched 활동: {[a.name for a in batched_activities]}")
        if not batched_activities:
            self.logger.warning("[진단] Batched 활동이 없어 그룹 생성 없이 반환")
            return Level1Result(
                groups={},
                applicants=applicants,
                dummy_count=0
            )
        # 직무별로 지원자 분류
        applicants_by_job = self._classify_by_job(applicants)
        self.logger.info(f"[진단] 직무별 지원자 분포: {{ {', '.join(f'{k}: {len(v)}명' for k,v in applicants_by_job.items())} }}")
        # 각 직무별로 공통 그룹 구성 (모든 batched 활동에서 재사용)
        job_groups = {}
        total_dummy_count = 0
        for job_code, job_applicants in applicants_by_job.items():
            # 이 직무의 지원자들이 수행하는 batched 활동들
            job_batched_activities = []
            for activity in batched_activities:
                # 상세 진단 로그: 지원자별 required_activities와 activity.name 비교
                for app in job_applicants:
                    match = activity.name in app.required_activities
                    self.logger.info(f"[진단] 지원자 {app.id}의 required_activities: {app.required_activities}, activity.name: {activity.name}, 포함여부: {match}")
                has_activity = any(activity.name in app.required_activities for app in job_applicants)
                self.logger.info(f"[진단] 직무 {job_code}에서 활동 '{activity.name}' 수행 지원자 존재 여부: {has_activity}")
                if has_activity:
                    job_batched_activities.append(activity)
            self.logger.info(f"[진단] {job_code} 직무의 batched 활동: {[a.name for a in job_batched_activities]}")
            if not job_batched_activities:
                self.logger.warning(f"[진단] {job_code} 직무에 batched 활동이 없어 그룹 생성 생략")
                continue
            min_capacity = max(act.min_capacity for act in job_batched_activities)
            max_capacity = min(act.max_capacity for act in job_batched_activities)
            self.logger.info(f"[진단] {job_code}: 지원자 {len(job_applicants)}명, 그룹 크기 {min_capacity}~{max_capacity}")
            groups, dummy_count = self._create_common_groups(
                job_applicants,
                job_code,
                min_capacity,
                max_capacity,
                job_batched_activities
            )
            self.logger.info(f"[진단] {job_code}: 생성된 그룹 수 {len(groups)}, 더미 {dummy_count}명")
            job_groups[job_code] = groups
            total_dummy_count += dummy_count
        # 활동별로 그룹 할당 (같은 그룹이 모든 활동 수행)
        all_groups = {}
        for activity in batched_activities:
            activity_groups = []
            for job_code, groups in job_groups.items():
                job_applicants = applicants_by_job[job_code]
                has_activity = any(activity.name in app.required_activities for app in job_applicants)
                if has_activity:
                    for group in groups:
                        activity_group = Group(
                            id=f"{job_code}_{group.id}",
                            activity_name=activity.name,
                            job_code=job_code,
                            applicants=group.applicants.copy(),
                            size=group.size
                        )
                        activity_groups.append(activity_group)
            if activity_groups:
                all_groups[activity.name] = activity_groups
            self.logger.info(f"[진단] 활동 {activity.name}에 할당된 그룹 수: {len(activity_groups)}")
        all_applicants = applicants.copy()
        added_dummies = set()
        for activity_groups in all_groups.values():
            for group in activity_groups:
                dummy_members = []
                if hasattr(group, 'dummy_ids'):
                    dummy_members = [mid for mid in group.dummy_ids if mid not in added_dummies]
                for dummy_id in dummy_members:
                    added_dummies.add(dummy_id)
                    parts = dummy_id.split("_")
                    dummy_job = parts[1] if len(parts) > 1 else group.job_code
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
        self.logger.info(f"[진단] 그룹 최적화 완료 (V2): {total_group_count}개 그룹, {total_dummy_count}명 더미")
        if total_group_count == 0:
            self.logger.error("[진단] 최종적으로 생성된 그룹이 0개입니다! 입력 데이터, min/max cap, 지원자-활동 매핑, 더미 생성 로직을 재점검하세요.")
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
        total_count = len(job_applicants)
        self.logger.info(f"[진단] _create_common_groups: {job_code}, 지원자 {total_count}명, 그룹 크기 {min_capacity}~{max_capacity}")
        if total_count < min_capacity:
            self.logger.error(f"[진단] 지원자 수({total_count})가 최소 그룹 크기({min_capacity})보다 적어 그룹 생성 불가!")
        group_count, dummy_count = calculate_group_count(
            total_count,
            min_capacity,
            max_capacity
        )
        self.logger.info(f"[진단] 그룹 수: {group_count}, 더미 수: {dummy_count}")
        dummy_ids = []
        if dummy_count > 0:
            for i in range(dummy_count):
                self.dummy_counter += 1
                dummy_id = f"DUMMY_{job_code}_{self.dummy_counter:03d}"
                dummy_ids.append(dummy_id)
        all_member_ids = [app.id for app in job_applicants] + dummy_ids
        groups = []
        if group_count == 0:
            self.logger.error(f"[진단] group_count가 0입니다! (지원자: {total_count}, min_cap: {min_capacity}, max_cap: {max_capacity})")
            return [], dummy_count
        members_per_group = len(all_member_ids) // group_count
        extra_members = len(all_member_ids) % group_count
        current_idx = 0
        for i in range(group_count):
            size = members_per_group + (1 if i < extra_members else 0)
            group_member_ids = all_member_ids[current_idx:current_idx + size]
            current_idx += size
            group_applicants = []
            for member_id in group_member_ids:
                if member_id.startswith("DUMMY_"):
                    continue
                else:
                    for app in job_applicants:
                        if app.id == member_id:
                            group_applicants.append(app)
                            break
            group = Group(
                id=f"G{i+1:03d}",
                activity_name="COMMON",
                job_code=job_code,
                applicants=group_applicants,
                size=len(group_member_ids)
            )
            group.dummy_ids = [mid for mid in group_member_ids if mid.startswith("DUMMY_")]
            groups.append(group)
        self.logger.info(f"[진단] _create_common_groups: 생성된 그룹 {len(groups)}개, 더미 {dummy_count}명")
        return groups, dummy_count 