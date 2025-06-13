# solver/group_formation.py
"""
Level 1: 그룹 구성 최적화 모듈
집단면접(batched mode)을 위한 지원자 그룹을 구성합니다.
"""

import pandas as pd
from ortools.sat.python import cp_model
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class GroupFormationOptimizer:
    """집단면접을 위한 그룹 구성 최적화"""
    
    def __init__(self, 
                 candidates: pd.DataFrame,
                 batched_activities: pd.DataFrame,
                 job_similarity_groups: Optional[List[List[str]]] = None,
                 prefer_job_separation: bool = True):
        """
        Args:
            candidates: 지원자 정보 (id, job_code 컬럼 필수)
            batched_activities: batched 모드 활동 정보 (activity, min_cap, max_cap 컬럼 필수)
            job_similarity_groups: 유사 직무 그룹 리스트 (예: [["DEV", "QA"], ["PM", "DESIGN"]])
            prefer_job_separation: 직무별 분리 우선 여부
        """
        self.candidates = candidates
        self.batched_activities = batched_activities
        self.job_similarity_groups = job_similarity_groups or []
        self.prefer_job_separation = prefer_job_separation
        
        # 그룹 크기 호환성 체크
        self._validate_group_size_compatibility()
        
    def _validate_group_size_compatibility(self):
        """모든 batched 활동의 그룹 크기 범위가 호환되는지 확인"""
        if self.batched_activities.empty:
            return
            
        min_caps = self.batched_activities['min_cap'].values
        max_caps = self.batched_activities['max_cap'].values
        
        # 공통 범위 찾기
        common_min = max(min_caps)
        common_max = min(max_caps)
        
        if common_min > common_max:
            raise ValueError(
                f"그룹 크기 호환성 오류: 모든 batched 활동이 공유할 수 있는 그룹 크기 범위가 없습니다.\n"
                f"최소 크기들: {min_caps}, 최대 크기들: {max_caps}"
            )
        
        self.group_size_min = common_min
        self.group_size_max = common_max
        
    def optimize(self, time_limit_sec: float = 60.0) -> Tuple[Dict[int, List[str]], str, str]:
        """
        그룹 구성 최적화 실행
        
        Returns:
            Tuple[groups, status, logs]:
                - groups: {그룹번호: [지원자ID 리스트]}
                - status: 최적화 상태 ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR")
                - logs: 실행 로그
        """
        model = cp_model.CpModel()
        logs = []
        
        try:
            # 기본 데이터 준비
            candidates_list = self.candidates['id'].tolist()
            job_codes = self.candidates.set_index('id')['job_code'].to_dict()
            n_candidates = len(candidates_list)
            
            # 최대 그룹 수 (모든 지원자가 최소 크기 그룹을 구성하는 경우)
            max_groups = (n_candidates + self.group_size_min - 1) // self.group_size_min
            
            # 변수 정의
            # x[i][g] = 1 if candidate i is in group g
            x = {}
            for i, cid in enumerate(candidates_list):
                for g in range(max_groups):
                    x[i, g] = model.NewBoolVar(f'x_{i}_{g}')
            
            # group_used[g] = 1 if group g is used
            group_used = [model.NewBoolVar(f'group_used_{g}') for g in range(max_groups)]
            
            # 제약 1: 모든 지원자는 정확히 하나의 그룹에 속함
            for i in range(n_candidates):
                model.Add(sum(x[i, g] for g in range(max_groups)) == 1)
            
            # 제약 2: 사용된 그룹의 크기 제약
            for g in range(max_groups):
                group_size = sum(x[i, g] for i in range(n_candidates))
                
                # 그룹이 사용되면 최소/최대 크기 제약 만족
                model.Add(group_size >= self.group_size_min).OnlyEnforceIf(group_used[g])
                model.Add(group_size <= self.group_size_max).OnlyEnforceIf(group_used[g])
                
                # 그룹이 사용되지 않으면 크기는 0
                model.Add(group_size == 0).OnlyEnforceIf(group_used[g].Not())
            
            # 제약 3: 직무별 분리 (선호사항인 경우)
            job_mixing_penalty = []
            if self.prefer_job_separation:
                # 각 그룹의 직무 혼합 정도 계산
                for g in range(max_groups):
                    # 각 직무별로 해당 그룹에 속한 인원 수 계산
                    job_counts = {}
                    unique_jobs = list(set(job_codes.values()))
                    
                    for job in unique_jobs:
                        job_members = [i for i, cid in enumerate(candidates_list) 
                                     if job_codes[cid] == job]
                        if job_members:
                            job_count = sum(x[i, g] for i in job_members)
                            job_counts[job] = job_count
                    
                    # 직무 혼합 페널티: 2개 이상의 직무가 섞인 경우
                    if len(job_counts) > 1:
                        # 각 직무 쌍에 대해 둘 다 존재하면 페널티
                        for j1, count1 in job_counts.items():
                            for j2, count2 in job_counts.items():
                                if j1 < j2:  # 중복 방지
                                    both_exist = model.NewBoolVar(f'both_{j1}_{j2}_g{g}')
                                    model.Add(count1 >= 1).OnlyEnforceIf(both_exist)
                                    model.Add(count2 >= 1).OnlyEnforceIf(both_exist)
                                    model.Add(count1 == 0).OnlyEnforceIf(both_exist.Not())
                                    job_mixing_penalty.append(both_exist)
            
            # 목적함수: 1) 사용 그룹 수 최소화, 2) 직무 혼합 최소화
            model.Minimize(
                sum(group_used) * 1000 +  # 그룹 수가 우선순위
                sum(job_mixing_penalty)   # 직무 혼합은 부차적
            )
            
            # 솔버 실행
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = time_limit_sec
            solver.parameters.log_search_progress = True
            status = solver.Solve(model)
            
            # 결과 처리
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                groups = {}
                for g in range(max_groups):
                    if solver.Value(group_used[g]) == 1:
                        members = []
                        for i, cid in enumerate(candidates_list):
                            if solver.Value(x[i, g]) == 1:
                                members.append(cid)
                        if members:
                            groups[g] = members
                
                # 로그 생성
                logs.append(f"그룹 구성 완료: {len(groups)}개 그룹")
                for g, members in sorted(groups.items()):
                    job_dist = {}
                    for cid in members:
                        job = job_codes[cid]
                        job_dist[job] = job_dist.get(job, 0) + 1
                    logs.append(f"  그룹 {g}: {len(members)}명 - {dict(job_dist)}")
                
                status_name = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
                return groups, status_name, "\n".join(logs)
                
            else:
                return {}, solver.StatusName(status), "그룹 구성 실패"
                
        except Exception as e:
            logger.error(f"그룹 구성 중 오류: {e}", exc_info=True)
            return {}, "ERROR", f"오류: {str(e)}"


def check_group_size_compatibility(activities_df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
    """
    모든 batched 활동의 그룹 크기 호환성을 체크합니다.
    
    Returns:
        Tuple[is_compatible, error_message]
    """
    batched_acts = activities_df[activities_df['mode'] == 'batched']
    
    if batched_acts.empty:
        return True, None
    
    min_caps = batched_acts['min_cap'].values
    max_caps = batched_acts['max_cap'].values
    
    common_min = max(min_caps)
    common_max = min(max_caps)
    
    if common_min > common_max:
        error_msg = f"그룹 크기 호환성 오류:\n"
        for _, act in batched_acts.iterrows():
            error_msg += f"- {act['activity']}: {act['min_cap']}-{act['max_cap']}명\n"
        error_msg += f"\n공통 범위를 찾을 수 없습니다. 최소값 조정이 필요합니다."
        return False, error_msg
    
    return True, None 