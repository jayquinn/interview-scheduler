"""
최적화된 멀티 날짜 스케줄러
- 날짜별 병렬 처리
- 메모리 효율화
- 캐싱 최적화
"""
from typing import Dict, List, Optional
from datetime import date
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time as time_module

from .types import (
    DateConfig, MultiDateResult, SingleDateResult, SchedulingContext,
    GlobalConfig, Room, Activity, ProgressInfo, ProgressCallback
)
from .optimized_scheduler import OptimizedScheduler, OptimizationConfig


class OptimizedMultiDateScheduler:
    """최적화된 멀티 날짜 스케줄러"""
    
    def __init__(self, optimization_config: OptimizationConfig = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.optimization_config = optimization_config or OptimizationConfig()
        
        # 통계
        self.overall_stats = {
            "cache_hit_rate": 0.0,
            "parallel_tasks": 0,
            "memory_cleanups": 0,
            "total_execution_time": 0.0
        }
    
    def schedule(
        self,
        date_plans: Dict[date, DateConfig],
        global_config: GlobalConfig,
        rooms: Dict[str, Room],
        activities: Dict[str, Activity],
        context: Optional[SchedulingContext] = None
    ) -> MultiDateResult:
        """
        최적화된 멀티 날짜 스케줄링 실행
        """
        start_time = time_module.time()
        
        result = MultiDateResult()
        result.total_applicants = sum(sum(plan.jobs.values()) for plan in date_plans.values())
        
        self.logger.info(f"최적화된 멀티 날짜 스케줄링 시작: {len(date_plans)}개 날짜, {result.total_applicants}명")
        
        try:
            # 날짜별 병렬 처리 여부 결정
            if (len(date_plans) > 1 and 
                self.optimization_config.enable_parallel_processing and
                result.total_applicants >= self.optimization_config.chunk_size_threshold):
                
                self.logger.info("병렬 처리 모드 활성화")
                self._schedule_dates_parallel(date_plans, result, context)
            else:
                self.logger.info("순차 처리 모드")
                self._schedule_dates_sequential(date_plans, result, context)
            
            # 결과 분석
            self._analyze_results(result)
            
        except Exception as e:
            self.logger.exception("최적화된 멀티 날짜 스케줄링 중 예외 발생")
            result.status = "ERROR"
            result.error_message = f"스케줄링 예외: {str(e)}"
        
        finally:
            # 통계 업데이트
            execution_time = time_module.time() - start_time
            self.overall_stats["total_execution_time"] = execution_time
            
            self.logger.info(f"최적화된 멀티 날짜 스케줄링 완료: {execution_time:.3f}초")
        
        return result
    
    def _schedule_dates_parallel(self, date_plans: Dict[date, DateConfig], 
                               result: MultiDateResult, context: Optional[SchedulingContext]):
        """날짜별 병렬 처리"""
        
        max_workers = min(len(date_plans), self.optimization_config.max_workers)
        self.overall_stats["parallel_tasks"] += 1
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 날짜별 작업 제출
            future_to_date = {}
            
            for target_date, date_config in date_plans.items():
                future = executor.submit(
                    self._schedule_single_date,
                    target_date,
                    date_config,
                    context
                )
                future_to_date[future] = target_date
            
            # 결과 수집
            completed_count = 0
            total_dates = len(date_plans)
            
            for future in as_completed(future_to_date):
                target_date = future_to_date[future]
                completed_count += 1
                
                try:
                    date_result = future.result(timeout=300)  # 5분 타임아웃
                    result.results[target_date] = date_result
                    
                    if date_result.status == "SUCCESS":
                        result.successful_dates.append(target_date)
                        result.scheduled_applicants += sum(date_config.jobs.values())
                    else:
                        result.failed_dates.append(target_date)
                    
                    # 진행 상황 보고
                    if context and context.progress_callback:
                        progress = completed_count / total_dates
                        context.progress_callback(ProgressInfo(
                            stage="MultiDate",
                            progress=progress,
                            message=f"날짜별 처리 완료: {completed_count}/{total_dates}",
                            details={"completed_dates": completed_count, "total_dates": total_dates}
                        ))
                    
                except Exception as e:
                    self.logger.error(f"날짜 {target_date} 병렬 처리 실패: {e}")
                    
                    # 실패한 날짜 결과 생성
                    failed_result = SingleDateResult(date=target_date, status="FAILED")
                    failed_result.error_message = f"병렬 처리 예외: {str(e)}"
                    
                    result.results[target_date] = failed_result
                    result.failed_dates.append(target_date)
    
    def _schedule_dates_sequential(self, date_plans: Dict[date, DateConfig], 
                                 result: MultiDateResult, context: Optional[SchedulingContext]):
        """날짜별 순차 처리"""
        
        total_dates = len(date_plans)
        completed_count = 0
        
        for target_date, date_config in date_plans.items():
            self.logger.info(f"날짜 처리 시작: {target_date}")
            
            try:
                date_result = self._schedule_single_date(target_date, date_config, context)
                result.results[target_date] = date_result
                
                if date_result.status == "SUCCESS":
                    result.successful_dates.append(target_date)
                    result.scheduled_applicants += sum(date_config.jobs.values())
                else:
                    result.failed_dates.append(target_date)
                
                completed_count += 1
                
                # 진행 상황 보고
                if context and context.progress_callback:
                    progress = completed_count / total_dates
                    context.progress_callback(ProgressInfo(
                        stage="MultiDate",
                        progress=progress,
                        message=f"날짜별 처리 완료: {completed_count}/{total_dates}",
                        details={"completed_dates": completed_count, "total_dates": total_dates}
                    ))
                
            except Exception as e:
                self.logger.error(f"날짜 {target_date} 순차 처리 실패: {e}")
                
                # 실패한 날짜 결과 생성
                failed_result = SingleDateResult(date=target_date, status="FAILED")
                failed_result.error_message = f"순차 처리 예외: {str(e)}"
                
                result.results[target_date] = failed_result
                result.failed_dates.append(target_date)
                completed_count += 1
    
    def _schedule_single_date(self, target_date: date, date_config: DateConfig, 
                            context: Optional[SchedulingContext]) -> SingleDateResult:
        """단일 날짜 스케줄링 (최적화된 스케줄러 사용)"""
        
        scheduler = OptimizedScheduler(self.logger)
        
        # 컨텍스트 복사 (날짜별 독립성 보장)
        date_context = None
        if context:
            date_context = SchedulingContext(
                progress_callback=context.progress_callback,
                enable_detailed_logging=context.enable_detailed_logging,
                real_time_updates=context.real_time_updates
            )
        
        result = scheduler.schedule(
            config=date_config,
            context=date_context,
            optimization_config=self.optimization_config
        )
        
        # 통계 수집
        if hasattr(scheduler, 'stats'):
            self._merge_stats(scheduler.stats)
        
        return result
    
    def _analyze_results(self, result: MultiDateResult):
        """결과 분석 및 상태 결정"""
        
        total_dates = len(result.results)
        successful_dates = len(result.successful_dates)
        
        if successful_dates == total_dates:
            result.status = "SUCCESS"
        elif successful_dates > 0:
            result.status = "PARTIAL"
        else:
            result.status = "FAILED"
        
        # 성공률 계산
        result.success_rate = successful_dates / total_dates if total_dates > 0 else 0
        
        self.logger.info(f"멀티 날짜 결과: {result.status}, 성공률 {result.success_rate*100:.1f}% "
                        f"({successful_dates}/{total_dates})")
    
    def _merge_stats(self, scheduler_stats: Dict):
        """개별 스케줄러 통계를 전체 통계에 병합"""
        
        self.overall_stats["parallel_tasks"] += scheduler_stats.get("parallel_tasks", 0)
        self.overall_stats["memory_cleanups"] += scheduler_stats.get("memory_cleanups", 0)
        
        # 캐시 적중률 평균 계산
        total_requests = scheduler_stats.get("cache_hits", 0) + scheduler_stats.get("cache_misses", 0)
        if total_requests > 0:
            hit_rate = scheduler_stats.get("cache_hits", 0) / total_requests * 100
            # 가중 평균으로 업데이트
            self.overall_stats["cache_hit_rate"] = (
                self.overall_stats["cache_hit_rate"] + hit_rate
            ) / 2
    
    def get_overall_stats(self) -> Dict:
        """전체 통계 반환"""
        return self.overall_stats.copy()
    
    def clear_cache(self):
        """캐시 정리"""
        # 개별 스케줄러들의 캐시는 각자 관리되므로 여기서는 통계만 초기화
        self.overall_stats = {
            "cache_hit_rate": 0.0,
            "parallel_tasks": 0,
            "memory_cleanups": 0,
            "total_execution_time": 0.0
        } 