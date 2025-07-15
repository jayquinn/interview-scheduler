"""
최적화된 멀티 날짜 스케줄러
- 날짜별 병렬 처리
- 메모리 효율화
- 캐싱 최적화
"""
from typing import Dict, List, Optional
from datetime import date, datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time as time_module
import traceback

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
        """
        단일 날짜 스케줄링 (최적화된 스케줄러 사용)
        """
        start_time = datetime.now()
        self.logger.info(f"[병목분석] [{target_date}] 단일 날짜 스케줄링 시작: {start_time}")
        
        scheduler = OptimizedScheduler(self.logger)
        
        # 컨텍스트 복사 (날짜별 독립성 보장)
        date_context = None
        if context:
            date_context = SchedulingContext(
                progress_callback=context.progress_callback,
                enable_detailed_logging=context.enable_detailed_logging,
                real_time_updates=context.real_time_updates
            )
        
        # 변수/제약조건 개수, 주요 제약조건 로그
        try:
            # 지원자 수 계산
            total_applicants = sum(date_config.jobs.values())
            self.logger.info(f"[병목분석] [{target_date}] 지원자 수: {total_applicants}명")
            
            # 활동 수 계산
            activity_count = len(date_config.activities)
            self.logger.info(f"[병목분석] [{target_date}] 활동 수: {activity_count}개")
            
            # 방 수 계산
            room_count = len(date_config.rooms)
            self.logger.info(f"[병목분석] [{target_date}] 방 수: {room_count}개")
            
            # 운영 시간 계산
            start_time_config, end_time_config = date_config.operating_hours
            operating_minutes = int((end_time_config - start_time_config).total_seconds() / 60)
            self.logger.info(f"[병목분석] [{target_date}] 운영 시간: {operating_minutes}분")
            
            # 예상 변수 수 계산 (대략적)
            estimated_variables = total_applicants * activity_count * room_count * (operating_minutes // 30)  # 30분 단위로 가정
            self.logger.info(f"[병목분석] [{target_date}] 예상 변수 수: {estimated_variables:,}개")
            
            # 선후행 제약 수
            precedence_count = len(date_config.precedence_rules)
            self.logger.info(f"[병목분석] [{target_date}] 선후행 제약: {precedence_count}개")
            
            # 복잡도 지수 계산
            complexity_index = (total_applicants * activity_count * room_count * precedence_count) / 1000
            self.logger.info(f"[병목분석] [{target_date}] 복잡도 지수: {complexity_index:.2f}")
            
            # 복잡도에 따른 예상 소요시간
            if complexity_index < 10:
                expected_time = "30초 이내"
            elif complexity_index < 50:
                expected_time = "1-2분"
            elif complexity_index < 100:
                expected_time = "2-5분"
            else:
                expected_time = "5분 이상"
            self.logger.info(f"[병목분석] [{target_date}] 예상 소요시간: {expected_time}")
            
            # 스케줄링 실행
            scheduler_start = datetime.now()
            self.logger.info(f"[병목분석] [{target_date}] CP-SAT 스케줄러 시작: {scheduler_start}")
            
            result = scheduler.schedule(date_config, date_context)
            
            scheduler_end = datetime.now()
            scheduler_elapsed = (scheduler_end - scheduler_start).total_seconds()
            self.logger.info(f"[병목분석] [{target_date}] CP-SAT 스케줄러 완료: {scheduler_end} (소요시간: {scheduler_elapsed:.2f}초)")
            
            # 결과 분석
            if result and hasattr(result, 'schedule'):
                scheduled_count = len(result.schedule) if result.schedule else 0
                self.logger.info(f"[병목분석] [{target_date}] 스케줄링 성공: {scheduled_count}개 항목")
                
                # 성공률 계산
                success_rate = (scheduled_count / (total_applicants * activity_count)) * 100 if total_applicants * activity_count > 0 else 0
                self.logger.info(f"[병목분석] [{target_date}] 성공률: {success_rate:.1f}%")
                
                # 시간당 처리량
                throughput = scheduled_count / (scheduler_elapsed / 3600) if scheduler_elapsed > 0 else 0
                self.logger.info(f"[병목분석] [{target_date}] 처리량: {throughput:.1f} 항목/시간")
            else:
                self.logger.warning(f"[병목분석] [{target_date}] 스케줄링 실패 또는 결과 없음")
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            self.logger.error(f"[병목분석] [{target_date}] 예외 발생: {str(e)} (소요시간: {elapsed:.2f}초)")
            self.logger.error(f"[병목분석] [{target_date}] 상세 오류: {traceback.format_exc()}")
            
            # 실패 시에도 부분 결과 반환 시도
            try:
                if hasattr(scheduler, 'get_partial_result'):
                    partial_result = scheduler.get_partial_result()
                    if partial_result:
                        self.logger.info(f"[병목분석] [{target_date}] 부분 결과 반환: {len(partial_result.schedule)}개 항목")
                        return partial_result
            except:
                pass
            
            # 최소한의 실패 결과 반환
            return SingleDateResult(
                date=datetime.combine(target_date, datetime.min.time()),
                status="FAILED",
                error_message=str(e),
                total_applicants=sum(date_config.jobs.values()),
                scheduled_applicants=0
            )
    
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