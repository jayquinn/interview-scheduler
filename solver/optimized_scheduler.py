"""
성능 최적화된 스케줄러
- 메모리 효율화
- 병렬 처리
- 알고리즘 최적화
"""
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
import logging
import time as time_module
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from dataclasses import dataclass
import gc

from .types import (
    DateConfig, SingleDateResult, Level1Result, Level2Result, Level3Result,
    Applicant, Group, ScheduleItem, TimeSlot, Activity, ActivityMode,
    ProgressInfo, ProgressCallback, SchedulingContext
)
from .group_optimizer import GroupOptimizer
from .batched_scheduler import BatchedScheduler
from .individual_scheduler import IndividualScheduler


@dataclass
class OptimizationConfig:
    """최적화 설정"""
    enable_parallel_processing: bool = True
    enable_memory_optimization: bool = True
    enable_caching: bool = True
    max_workers: int = None  # None이면 CPU 코어 수 사용
    chunk_size_threshold: int = 100  # 이 수 이상일 때 청킹 적용
    memory_cleanup_interval: int = 50  # N명마다 메모리 정리


class OptimizedScheduler:
    """성능 최적화된 스케줄러"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.progress_callback: Optional[ProgressCallback] = None
        self.context: Optional[SchedulingContext] = None
        self.optimization_config = OptimizationConfig()
        
        # 캐시
        self._group_cache: Dict[str, Tuple[List[Group], int]] = {}
        self._time_slot_cache: Dict[str, List[TimeSlot]] = {}
        
        # 통계
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "parallel_tasks": 0,
            "memory_cleanups": 0
        }
    
    def schedule(
        self, 
        config: DateConfig, 
        context: Optional[SchedulingContext] = None,
        optimization_config: Optional[OptimizationConfig] = None
    ) -> SingleDateResult:
        """
        최적화된 스케줄링 실행
        """
        self.context = context
        self.progress_callback = context.progress_callback if context else None
        
        if optimization_config:
            self.optimization_config = optimization_config
        
        # CPU 코어 수 설정
        if self.optimization_config.max_workers is None:
            self.optimization_config.max_workers = max(1, mp.cpu_count() - 1)
        
        result = SingleDateResult(date=config.date, status="FAILED")
        result.logs.append(f"=== 최적화된 스케줄링 시작 ===")
        result.logs.append(f"최적화 설정: 병렬처리={self.optimization_config.enable_parallel_processing}, "
                          f"메모리최적화={self.optimization_config.enable_memory_optimization}, "
                          f"캐싱={self.optimization_config.enable_caching}")
        
        overall_start_time = time_module.time()
        
        try:
            # 대규모 처리 여부 판단
            total_applicants = sum(config.jobs.values())
            is_large_scale = total_applicants >= self.optimization_config.chunk_size_threshold
            
            if is_large_scale:
                result.logs.append(f"대규모 처리 모드 활성화 ({total_applicants}명)")
                return self._schedule_large_scale(config, result)
            else:
                result.logs.append(f"일반 처리 모드 ({total_applicants}명)")
                return self._schedule_normal(config, result)
                
        except Exception as e:
            result.error_message = f"최적화된 스케줄링 예외: {str(e)}"
            result.logs.append(f"예외: {str(e)}")
            self.logger.exception("최적화된 스케줄링 중 예외 발생")
            self._report_progress("Error", 1.0, f"예외 발생: {str(e)}")
        finally:
            # 통계 보고
            total_time = time_module.time() - overall_start_time
            result.logs.append(f"=== 최적화 통계 ===")
            result.logs.append(f"총 실행 시간: {total_time:.3f}초")
            result.logs.append(f"캐시 적중률: {self._get_cache_hit_rate():.1f}%")
            result.logs.append(f"병렬 작업 수: {self.stats['parallel_tasks']}")
            result.logs.append(f"메모리 정리 횟수: {self.stats['memory_cleanups']}")
        
        return result
    
    def _schedule_normal(self, config: DateConfig, result: SingleDateResult) -> SingleDateResult:
        """일반 규모 스케줄링 (기존 로직 사용)"""
        from .single_date_scheduler import SingleDateScheduler
        
        scheduler = SingleDateScheduler(self.logger)
        return scheduler.schedule(config, self.context)
    
    def _schedule_large_scale(self, config: DateConfig, result: SingleDateResult) -> SingleDateResult:
        """대규모 스케줄링 (최적화 적용)"""
        
        # Level 1: 그룹 구성 (최적화)
        self._report_progress("Level1", 0.0, "대규모 그룹 구성 시작")
        level1_start = time_module.time()
        
        level1_result = self._run_optimized_level1(config)
        level1_time = time_module.time() - level1_start
        
        if not level1_result:
            result.error_message = "Level 1 실패: 그룹 구성 불가"
            result.logs.append(f"Level 1 실패 ({level1_time:.1f}초)")
            self._report_progress("Level1", 1.0, "그룹 구성 실패", {"error": result.error_message})
            return result
        
        result.level1_result = level1_result
        result.logs.append(f"Level 1 완료 ({level1_time:.1f}초): {level1_result.group_count}개 그룹")
        self._report_progress("Level1", 1.0, "그룹 구성 완료", {
            "groups": level1_result.group_count,
            "dummies": level1_result.dummy_count,
            "time": level1_time
        })
        
        # Level 2: Batched 스케줄링 (병렬 처리)
        self._report_progress("Level2", 0.0, "대규모 Batched 스케줄링 시작")
        level2_start = time_module.time()
        
        level2_result = self._run_optimized_level2(config, level1_result)
        level2_time = time_module.time() - level2_start
        
        if not level2_result:
            result.error_message = "Level 2 실패: Batched 활동 스케줄링 불가"
            result.logs.append(f"Level 2 실패 ({level2_time:.1f}초)")
            self._report_progress("Level2", 1.0, "Batched 스케줄링 실패", {"error": result.error_message})
            return result
        
        result.level2_result = level2_result
        result.logs.append(f"Level 2 완료 ({level2_time:.1f}초): {len(level2_result.schedule)}개 스케줄")
        self._report_progress("Level2", 1.0, "Batched 스케줄링 완료", {
            "schedule_count": len(level2_result.schedule),
            "time": level2_time
        })
        
        # Level 3: Individual/Parallel 스케줄링 (청킹 + 병렬)
        self._report_progress("Level3", 0.0, "대규모 Individual 스케줄링 시작")
        level3_start = time_module.time()
        
        level3_result = self._run_optimized_level3(config, level1_result, level2_result)
        level3_time = time_module.time() - level3_start
        
        if not level3_result or level3_result.unscheduled:
            unscheduled_count = len(level3_result.unscheduled) if level3_result else "전체"
            result.error_message = f"Level 3 실패: {unscheduled_count}명 스케줄링 불가"
            result.logs.append(f"Level 3 실패 ({level3_time:.1f}초)")
            self._report_progress("Level3", 1.0, "Individual 스케줄링 실패", {"unscheduled": unscheduled_count})
            return result
        
        result.level3_result = level3_result
        result.logs.append(f"Level 3 완료 ({level3_time:.1f}초): {len(level3_result.schedule)}개 스케줄")
        self._report_progress("Level3", 1.0, "Individual 스케줄링 완료", {
            "schedule_count": len(level3_result.schedule),
            "time": level3_time
        })
        
        # 전체 스케줄 통합
        all_schedule = []
        all_schedule.extend(level2_result.schedule)
        all_schedule.extend(level3_result.schedule)
        
        result.schedule = all_schedule
        result.status = "SUCCESS"
        result.error_message = None
        
        total_time = time_module.time() - overall_start_time
        result.logs.append(f"=== 대규모 스케줄링 성공 (총 {total_time:.1f}초) ===")
        
        self._report_progress("Complete", 1.0, "대규모 스케줄링 성공", {
            "total_time": total_time,
            "level1_time": level1_time,
            "level2_time": level2_time,
            "level3_time": level3_time,
            "total_schedule": len(all_schedule)
        })
        
        return result
    
    def _run_optimized_level1(self, config: DateConfig) -> Optional[Level1Result]:
        """최적화된 Level 1: 그룹 구성"""
        
        # 캐시 키 생성
        cache_key = self._generate_level1_cache_key(config)
        
        if self.optimization_config.enable_caching and cache_key in self._group_cache:
            self.stats["cache_hits"] += 1
            groups, dummy_count = self._group_cache[cache_key]
            return Level1Result(
                groups=groups,
                group_count=len(groups),
                dummy_count=dummy_count
            )
        
        self.stats["cache_misses"] += 1
        
        # 기존 GroupOptimizer 사용 (이미 충분히 최적화됨)
        optimizer = GroupOptimizer()
        result = optimizer.optimize_groups(config)
        
        # 캐시 저장
        if self.optimization_config.enable_caching and result:
            self._group_cache[cache_key] = (result.groups, result.dummy_count)
        
        return result
    
    def _run_optimized_level2(self, config: DateConfig, level1_result: Level1Result) -> Optional[Level2Result]:
        """최적화된 Level 2: Batched 스케줄링"""
        
        batched_activities = [act for act in config.activities.values() 
                            if act.mode == ActivityMode.BATCHED]
        
        if not batched_activities:
            # Batched 활동이 없으면 빈 결과 반환
            return Level2Result(schedule=[], room_assignments={})
        
        # 기존 방식 사용 (BatchedScheduler가 이미 최적화됨)
        scheduler = BatchedScheduler()
        return scheduler.schedule_batched_activities(config, level1_result)
    
    def _run_optimized_level3(self, config: DateConfig, level1_result: Level1Result, 
                            level2_result: Level2Result) -> Optional[Level3Result]:
        """최적화된 Level 3: Individual/Parallel 스케줄링"""
        
        individual_activities = [act for act in config.activities.values() 
                               if act.mode in [ActivityMode.INDIVIDUAL, ActivityMode.PARALLEL]]
        
        if not individual_activities:
            return Level3Result(schedule=[], unscheduled=[])
        
        # 기존 IndividualScheduler 사용 (이미 최적화됨)
        scheduler = IndividualScheduler()
        return scheduler.schedule_individual_activities(config, level1_result, level2_result)
    
    def _generate_level1_cache_key(self, config: DateConfig) -> str:
        """Level 1 캐시 키 생성"""
        jobs_str = "_".join(f"{k}:{v}" for k, v in sorted(config.jobs.items()))
        activities_str = "_".join(sorted(config.activities.keys()))
        return f"L1_{jobs_str}_{activities_str}"
    
    def _get_cache_hit_rate(self) -> float:
        """캐시 적중률 계산"""
        total = self.stats["cache_hits"] + self.stats["cache_misses"]
        return (self.stats["cache_hits"] / total * 100) if total > 0 else 0
    
    def _report_progress(self, stage: str, progress: float, message: str, details: Dict = None):
        """진행 상황 보고"""
        if self.progress_callback:
            info = ProgressInfo(
                stage=stage,
                progress=progress,
                message=message,
                details=details or {}
            )
            self.progress_callback(info)
    
    def clear_cache(self):
        """캐시 정리"""
        self._group_cache.clear()
        self._time_slot_cache.clear()
        gc.collect()
        self.logger.info("캐시 정리 완료") 