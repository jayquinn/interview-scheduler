# solver/hierarchical_solver.py
"""
3단계 계층적 솔버 통합 모듈
Level 1 → Level 2 → Level 3 순서로 최적화를 수행하고 백트래킹을 관리합니다.
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
import time

from .group_formation import GroupFormationOptimizer, check_group_size_compatibility
from .batched_scheduler import BatchedScheduler, convert_schedule_to_dataframe
from .mixed_scheduler import MixedScheduler

logger = logging.getLogger(__name__)


class HierarchicalSolver:
    """3단계 계층적 최적화 솔버"""
    
    def __init__(self, config: Dict):
        """
        Args:
            config: 전체 설정 딕셔너리
                - activities: 활동 정보 DataFrame
                - candidates: 지원자 정보 DataFrame  
                - job_acts_map: 직무별 활동 매핑
                - room_info: 방 정보
                - oper_hours: 운영 시간
                - precedence: 선후행 제약
                - job_similarity_groups: 유사 직무 그룹 (선택)
                - prefer_job_separation: 직무별 분리 우선 (기본값: True)
                - min_gap_min: 활동 간 최소 간격 (기본값: 5)
                - the_date: 면접 날짜
        """
        self.config = config
        self.activities = config['activities']
        self.candidates = config['candidates']
        self.room_info = config['room_info']
        self.oper_hours = config['oper_hours']
        self.precedence = config.get('precedence', [])
        self.min_gap_min = config.get('min_gap_min', 5)
        self.the_date = config['the_date']
        
        # 활동을 모드별로 분류
        self.individual_activities = self.activities[self.activities['mode'] == 'individual']
        self.parallel_activities = self.activities[self.activities['mode'] == 'parallel']
        self.batched_activities = self.activities[self.activities['mode'] == 'batched']
        
        # 유사 직무 그룹과 직무별 분리 설정
        self.job_similarity_groups = config.get('job_similarity_groups', [])
        self.prefer_job_separation = config.get('prefer_job_separation', True)
        
        # 시간 제한 설정
        self.total_time_limit = config.get('time_limit_sec', 300.0)  # 전체 5분
        self.level1_time_limit = 60.0  # Level 1: 1분
        self.level2_time_limit = 120.0  # Level 2: 2분
        self.level3_time_limit = 120.0  # Level 3: 2분
        
        # 백트래킹 설정
        self.max_backtrack_attempts = config.get('max_backtrack_attempts', 3)
        
    def solve(self) -> Tuple[pd.DataFrame, str, str]:
        """
        3단계 계층적 최적화 실행
        
        Returns:
            Tuple[schedule_df, status, logs]:
                - schedule_df: 최종 스케줄 DataFrame
                - status: 최종 상태
                - logs: 실행 로그
        """
        start_time = time.time()
        all_logs = []
        level_times = {}  # 각 레벨별 실행 시간 저장
        
        try:
            # 그룹 크기 호환성 체크
            is_compatible, error_msg = check_group_size_compatibility(self.activities)
            if not is_compatible:
                return pd.DataFrame(), "INCOMPATIBLE", error_msg
            
            # Batched 활동이 없는 경우 기존 솔버로 fallback
            if self.batched_activities.empty:
                all_logs.append("Batched 활동이 없습니다. 기존 individual 솔버로 처리합니다.")
                return self._solve_individual_only()
            
            # Level 1: 그룹 구성
            all_logs.append("=== Level 1: 그룹 구성 시작 ===")
            level1_start = time.time()
            groups, level1_status, level1_logs = self._solve_level1()
            level_times['Level 1'] = time.time() - level1_start
            all_logs.append(level1_logs)
            all_logs.append(f"Level 1 실행 시간: {level_times['Level 1']:.1f}초")
            
            if level1_status not in ["OPTIMAL", "FEASIBLE"]:
                return pd.DataFrame(), f"LEVEL1_{level1_status}", "\n".join(all_logs)
            
            # Level 2: Batched 활동 스케줄링
            all_logs.append("\n=== Level 2: Batched 활동 스케줄링 시작 ===")
            
            level2_success = False
            batched_schedule = None
            backtrack_count = 0
            
            for attempt in range(self.max_backtrack_attempts):
                if time.time() - start_time > self.total_time_limit:
                    all_logs.append("전체 시간 제한 초과")
                    break
                
                all_logs.append(f"Level 2 시도 {attempt + 1}/{self.max_backtrack_attempts}")
                
                level2_start = time.time()
                batched_schedule, level2_status, level2_logs = self._solve_level2(groups)
                level2_time = time.time() - level2_start
                if f'Level 2-{attempt+1}' not in level_times:
                    level_times[f'Level 2-{attempt+1}'] = level2_time
                
                all_logs.append(level2_logs)
                all_logs.append(f"Level 2 시도 {attempt+1} 실행 시간: {level2_time:.1f}초")
                
                if level2_status in ["OPTIMAL", "FEASIBLE"]:
                    level2_success = True
                    break
                elif attempt < self.max_backtrack_attempts - 1:
                    # Level 1로 백트래킹
                    backtrack_count += 1
                    all_logs.append(f"Level 2 실패. Level 1로 백트래킹... (백트래킹 횟수: {backtrack_count})")
                    
                    level1_start = time.time()
                    groups, level1_status, level1_logs = self._solve_level1_with_hint(attempt + 1)
                    level_times[f'Level 1 백트래킹-{backtrack_count}'] = time.time() - level1_start
                    
                    all_logs.append(level1_logs)
                    
                    if level1_status not in ["OPTIMAL", "FEASIBLE"]:
                        break
            
            if not level2_success:
                return pd.DataFrame(), f"LEVEL2_FAILED", "\n".join(all_logs)
            
            # Level 3: Individual/Parallel 활동 스케줄링
            all_logs.append("\n=== Level 3: Individual/Parallel 활동 스케줄링 시작 ===")
            
            level3_success = False
            final_schedule = None
            
            for attempt in range(self.max_backtrack_attempts):
                if time.time() - start_time > self.total_time_limit:
                    all_logs.append("전체 시간 제한 초과")
                    break
                
                all_logs.append(f"Level 3 시도 {attempt + 1}/{self.max_backtrack_attempts}")
                
                level3_start = time.time()
                final_schedule, level3_status, level3_logs = self._solve_level3(groups, batched_schedule)
                level3_time = time.time() - level3_start
                level_times[f'Level 3-{attempt+1}'] = level3_time
                
                all_logs.append(level3_logs)
                all_logs.append(f"Level 3 시도 {attempt+1} 실행 시간: {level3_time:.1f}초")
                
                if level3_status in ["OPTIMAL", "FEASIBLE"]:
                    level3_success = True
                    break
                elif attempt < self.max_backtrack_attempts - 1:
                    # Level 2로 백트래킹
                    backtrack_count += 1
                    all_logs.append(f"Level 3 실패. Level 2로 백트래킹... (백트래킹 횟수: {backtrack_count})")
                    
                    level2_start = time.time()
                    batched_schedule, level2_status, level2_logs = self._solve_level2_with_hint(
                        groups, attempt + 1
                    )
                    level_times[f'Level 2 백트래킹-{backtrack_count}'] = time.time() - level2_start
                    
                    all_logs.append(level2_logs)
                    
                    if level2_status not in ["OPTIMAL", "FEASIBLE"]:
                        # Level 1로 다시 백트래킹
                        all_logs.append(f"Level 2도 실패. Level 1로 백트래킹...")
                        groups, level1_status, level1_logs = self._solve_level1_with_hint(
                            attempt + 1
                        )
                        all_logs.append(level1_logs)
                        
                        if level1_status not in ["OPTIMAL", "FEASIBLE"]:
                            break
                        
                        # Level 2 재시도
                        batched_schedule, level2_status, level2_logs = self._solve_level2(groups)
                        all_logs.append(level2_logs)
                        
                        if level2_status not in ["OPTIMAL", "FEASIBLE"]:
                            break
            
            if not level3_success:
                return pd.DataFrame(), f"LEVEL3_FAILED", "\n".join(all_logs)
            
            # 최종 결과를 wide format으로 변환
            wide_schedule = self._convert_to_wide_format(final_schedule)
            
            elapsed_time = time.time() - start_time
            
            # 성능 요약
            all_logs.append(f"\n=== 최적화 완료 (총 소요시간: {elapsed_time:.1f}초) ===")
            all_logs.append("**레벨별 실행 시간 요약:**")
            for level, duration in level_times.items():
                all_logs.append(f"  - {level}: {duration:.1f}초")
            all_logs.append(f"**백트래킹 발생 횟수:** {backtrack_count}회")
            
            return wide_schedule, "OPTIMAL", "\n".join(all_logs)
            
        except Exception as e:
            logger.error(f"계층적 솔버 오류: {e}", exc_info=True)
            all_logs.append(f"오류 발생: {str(e)}")
            return pd.DataFrame(), "ERROR", "\n".join(all_logs)
    
    def _solve_level1(self) -> Tuple[Dict[int, List[str]], str, str]:
        """Level 1: 그룹 구성 최적화"""
        optimizer = GroupFormationOptimizer(
            candidates=self.candidates,
            batched_activities=self.batched_activities,
            job_similarity_groups=self.job_similarity_groups,
            prefer_job_separation=self.prefer_job_separation
        )
        
        return optimizer.optimize(time_limit_sec=self.level1_time_limit)
    
    def _solve_level1_with_hint(self, hint: int) -> Tuple[Dict[int, List[str]], str, str]:
        """Level 1: 힌트를 사용한 그룹 구성 (백트래킹용)"""
        # 힌트에 따라 파라미터 조정
        # 예: 그룹 크기 범위 확대, 직무 혼합 허용 등
        modified_activities = self.batched_activities.copy()
        
        # 그룹 크기 범위를 약간 확대
        if hint > 0:
            modified_activities['min_cap'] = modified_activities['min_cap'] - hint
            modified_activities['max_cap'] = modified_activities['max_cap'] + hint
            
        # 직무별 분리 조건 완화
        prefer_separation = self.prefer_job_separation if hint < 2 else False
        
        optimizer = GroupFormationOptimizer(
            candidates=self.candidates,
            batched_activities=modified_activities,
            job_similarity_groups=self.job_similarity_groups,
            prefer_job_separation=prefer_separation
        )
        
        return optimizer.optimize(time_limit_sec=self.level1_time_limit)
    
    def _solve_level2(self, groups: Dict[int, List[str]]) -> Tuple[Dict, str, str]:
        """Level 2: Batched 활동 스케줄링"""
        scheduler = BatchedScheduler(
            groups=groups,
            batched_activities=self.batched_activities,
            room_info=self.room_info,
            oper_hours=self.oper_hours,
            precedence_rules=self.precedence,
            min_gap_min=self.min_gap_min
        )
        
        return scheduler.optimize(time_limit_sec=self.level2_time_limit)
    
    def _solve_level2_with_hint(self, groups: Dict[int, List[str]], hint: int) -> Tuple[Dict, str, str]:
        """Level 2: 힌트를 사용한 Batched 스케줄링 (백트래킹용)"""
        # 힌트에 따라 제약 완화
        relaxed_min_gap = max(0, self.min_gap_min - hint * 5)
        
        scheduler = BatchedScheduler(
            groups=groups,
            batched_activities=self.batched_activities,
            room_info=self.room_info,
            oper_hours=self.oper_hours,
            precedence_rules=self.precedence,
            min_gap_min=relaxed_min_gap
        )
        
        return scheduler.optimize(time_limit_sec=self.level2_time_limit)
    
    def _solve_level3(self, groups: Dict[int, List[str]], batched_schedule: Dict) -> Tuple[pd.DataFrame, str, str]:
        """Level 3: Individual/Parallel 활동 스케줄링"""
        scheduler = MixedScheduler(
            candidates=self.candidates,
            groups=groups,
            batched_schedule=batched_schedule,
            individual_activities=self.individual_activities,
            parallel_activities=self.parallel_activities,
            room_info=self.room_info,
            oper_hours=self.oper_hours,
            precedence_rules=self.precedence,
            min_gap_min=self.min_gap_min
        )
        
        return scheduler.optimize(time_limit_sec=self.level3_time_limit)
    
    def _solve_individual_only(self) -> Tuple[pd.DataFrame, str, str]:
        """Batched 활동이 없는 경우 기존 방식으로 처리"""
        # 여기서는 간단히 에러 반환 (실제로는 기존 솔버 호출)
        return pd.DataFrame(), "NOT_IMPLEMENTED", "Individual only mode는 기존 솔버를 사용하세요"
    
    def _convert_to_wide_format(self, schedule_df: pd.DataFrame) -> pd.DataFrame:
        """Long format 스케줄을 Wide format으로 변환"""
        if schedule_df.empty:
            return pd.DataFrame()
        
        # 시간을 datetime으로 변환
        base_time = pd.to_datetime(self.the_date.date().strftime('%Y-%m-%d') + ' 00:00:00')
        schedule_df['start'] = base_time + pd.to_timedelta(schedule_df['start_min'], unit='minutes')
        schedule_df['end'] = base_time + pd.to_timedelta(schedule_df['end_min'], unit='minutes')
        
        # Wide format으로 변환
        wide_df = schedule_df.pivot_table(
            index=['id', 'group_id'],
            columns='activity',
            values=['start', 'end', 'room'],
            aggfunc='first'
        ).reset_index()
        
        # 컬럼명 정리
        wide_df.columns = ['_'.join(col).strip() if isinstance(col, tuple) and col[1] else col[0] 
                          for col in wide_df.columns]
        
        # interview_date와 job_code 추가
        candidate_info = self.candidates.set_index('id')[['job_code']].to_dict()['job_code']
        wide_df['interview_date'] = self.the_date
        wide_df['code'] = wide_df['id'].map(candidate_info)
        
        # 컬럼 순서 조정
        base_cols = ['id', 'interview_date', 'code', 'group_id']
        other_cols = [col for col in wide_df.columns if col not in base_cols]
        wide_df = wide_df[base_cols + other_cols]
        
        return wide_df 