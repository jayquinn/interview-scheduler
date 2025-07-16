"""
면접 스케줄링 시스템 API
외부에서 사용할 메인 인터페이스
"""
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime, time, timedelta
import logging
import pandas as pd

from .types import (
    DatePlan, GlobalConfig, MultiDateResult, PrecedenceRule,
    ActivityMode, ActivityType, Activity, Room, DateConfig,
    ProgressCallback, SchedulingContext
)
from .multi_date_scheduler import MultiDateScheduler
from .single_date_scheduler import SingleDateScheduler


def schedule_interviews(
    date_plans: Dict[str, Dict],
    global_config: Dict,
    rooms: Dict,
    activities: Dict,
    logger: Optional[logging.Logger] = None
) -> Union[MultiDateResult, Dict]:
    """
    면접 스케줄링 메인 API
    
    Args:
        date_plans: 날짜별 설정
            {
                "2025-07-01": {
                    "jobs": {"JOB01": 23, "JOB02": 20},
                    "selected_activities": ["토론면접", "발표면접"],
                    "overrides": {...}  # Optional
                }
            }
            
        global_config: 전역 설정
            {
                "precedence": [("발표준비", "발표면접", 0, True)],
                "operating_hours": {"start": "09:00", "end": "17:30"},
                "batched_group_sizes": {"토론면접": [4, 6]},
                "global_gap_min": 5,
                "max_stay_hours": 8
            }
            
        rooms: 방 설정
            {
                "토론면접실": {"count": 2, "capacity": 6},
                "발표면접실": {"count": 2, "capacity": 1}
            }
            
        activities: 활동 설정
            {
                "토론면접": {
                    "mode": "batched",
                    "duration_min": 30,
                    "room_type": "토론면접실",
                    "min_capacity": 4,
                    "max_capacity": 6
                }
            }
            
    Returns:
        스케줄링 결과 (성공시 DataFrame 포함)
    """
    
    # 1. 입력 데이터 변환
    try:
        # DatePlan 객체들로 변환
        date_plan_objects = {}
        for date_str, plan_data in date_plans.items():
            date = datetime.strptime(date_str, "%Y-%m-%d")
            date_plan_objects[date] = DatePlan(
                date=date,
                jobs=plan_data["jobs"],
                selected_activities=plan_data["selected_activities"],
                overrides=plan_data.get("overrides")
            )
        
        # GlobalConfig 객체로 변환
        precedence_rules = []
        for rule in global_config.get("precedence", []):
            if isinstance(rule, (list, tuple)):
                precedence_rules.append(PrecedenceRule(
                    predecessor=rule[0],
                    successor=rule[1],
                    gap_min=rule[2] if len(rule) > 2 else 0,
                    is_adjacent=rule[3] if len(rule) > 3 else False
                ))
        
        # 운영시간 변환
        op_hours = global_config.get("operating_hours", {})
        if isinstance(op_hours, dict) and "start" in op_hours:
            # 단일 설정을 default로
            operating_hours = {
                "default": (
                    time.fromisoformat(op_hours["start"]),
                    time.fromisoformat(op_hours["end"])
                )
            }
        else:
            operating_hours = {"default": (time(9, 0), time(17, 30))}
        
        # batched 그룹 크기 변환
        batched_sizes = {}
        for act, sizes in global_config.get("batched_group_sizes", {}).items():
            if isinstance(sizes, list) and len(sizes) >= 2:
                batched_sizes[act] = (sizes[0], sizes[1])
        
        global_config_obj = GlobalConfig(
            precedence_rules=precedence_rules,
            operating_hours=operating_hours,
            room_settings=rooms,  # 그대로 사용
            time_settings={act: data["duration_min"] for act, data in activities.items()},
            batched_group_sizes=batched_sizes,
            global_gap_min=global_config.get("global_gap_min", 5),
            max_stay_hours=global_config.get("max_stay_hours", 8)
        )
        
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"입력 데이터 변환 오류: {str(e)}"
        }
    
    # 2. 스케줄러 실행
    scheduler = MultiDateScheduler(logger)
    
    # 검증
    errors = scheduler.validate_config(date_plan_objects, global_config_obj)
    if errors:
        return {
            "status": "VALIDATION_ERROR",
            "errors": errors
        }
    
    # 스케줄링
    result = scheduler.schedule(
        date_plan_objects,
        global_config_obj,
        rooms,
        activities
    )
    
    # 3. 결과 반환
    if result.status == "SUCCESS":
        # DataFrame으로 변환하여 반환
        df = result.to_dataframe()
        return {
            "status": "SUCCESS",
            "schedule": df,
            "summary": {
                "total_applicants": result.total_applicants,
                "scheduled_applicants": result.scheduled_applicants,
                "dates": len(result.results)
            }
        }
    else:
        # 실패 정보 반환
        failed_info = {}
        for date, date_result in result.results.items():
            if date_result.status == "FAILED":
                failed_info[date.strftime("%Y-%m-%d")] = {
                    "error": date_result.error_message,
                    "logs": date_result.logs
                }
        
        return {
            "status": result.status,
            "scheduled_applicants": result.scheduled_applicants,
            "total_applicants": result.total_applicants,
            "failed_dates": [d.strftime("%Y-%m-%d") for d in result.failed_dates],
            "failed_info": failed_info,
            "partial_schedule": result.to_dataframe() if result.scheduled_applicants > 0 else None
        }


def convert_to_wide_format(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """
    스케줄 DataFrame을 기존 시스템과 호환되는 wide 형식으로 변환
    
    Args:
        schedule_df: long 형식의 스케줄 DataFrame
        
    Returns:
        wide 형식의 DataFrame (활동별 컬럼)
    """
    if schedule_df.empty:
        return pd.DataFrame()
    
    # 피벗 테이블 생성
    wide_df = schedule_df.pivot_table(
        index=['id', 'interview_date'],
        columns='activity',
        values=['start_time', 'end_time', 'room'],
        aggfunc='first'
    ).reset_index()
    
    # 컬럼명 평탄화
    wide_df.columns = ['_'.join(col).strip() if isinstance(col, tuple) and col[1] else col[0] 
                       for col in wide_df.columns]
    wide_df = wide_df.rename(columns={'id_': 'id', 'interview_date_': 'interview_date'})
    
    # 시간 형식 변환
    time_cols = [col for col in wide_df.columns if col.startswith(('start_time_', 'end_time_'))]
    for col in time_cols:
        wide_df[col] = pd.to_datetime(wide_df[col]).dt.strftime('%H:%M')
    
    # 컬럼명 변경 (기존 형식에 맞게)
    rename_map = {}
    for col in wide_df.columns:
        if col.startswith('start_time_'):
            activity = col[len('start_time_'):]
            rename_map[col] = f'start_{activity}'
        elif col.startswith('end_time_'):
            activity = col[len('end_time_'):]
            rename_map[col] = f'end_{activity}'
        elif col.startswith('room_'):
            activity = col[len('room_'):]
            rename_map[col] = f'loc_{activity}'
    
    wide_df = wide_df.rename(columns=rename_map)
    
    # 직무 코드 추가
    wide_df['code'] = wide_df['id'].str.split('_').str[0]
    
    # 컬럼 순서 정렬
    base_cols = ['id', 'interview_date', 'code']
    other_cols = sorted([col for col in wide_df.columns if col not in base_cols])
    
    return wide_df[base_cols + other_cols]


# 편의 함수들
def create_default_global_config() -> Dict:
    """기본 전역 설정 생성"""
    return {
        "precedence": [],
        "operating_hours": {"start": "09:00", "end": "17:30"},
        "batched_group_sizes": {},
        "global_gap_min": 5,
        "max_stay_hours": 8
    }


def create_date_plan(
    date: str,
    jobs: Dict[str, int],
    activities: List[str],
    overrides: Optional[Dict] = None
) -> Dict:
    """날짜별 계획 생성 헬퍼"""
    return {
        "date": date,
        "jobs": jobs,
        "selected_activities": activities,
        "overrides": overrides or {}
    }


def solve_for_days_v2(
    cfg_ui: dict, 
    params: dict = None, 
    debug: bool = False,
    progress_callback: Optional[ProgressCallback] = None
) -> Tuple[str, pd.DataFrame, str, int]:
    """
    새로운 계층적 스케줄러를 사용하여 UI 요청 처리
    
    기존 solve_for_days와 호환되는 인터페이스 제공
    
    Args:
        cfg_ui: UI 설정 딕셔너리
        params: 추가 파라미터
        debug: 디버그 모드
        progress_callback: 실시간 진행 상황 콜백 함수
    
    Returns:
        (status, final_wide_df, logs, daily_limit)
    """
    try:
        # 로깅 설정
        log_level = logging.DEBUG if debug else logging.WARNING
        logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
        logger = logging.getLogger(__name__)
        
        logs_buffer = []
        
        # 🚀 스마트 통합 로직 적용
        cfg_ui_optimized = _apply_smart_integration(cfg_ui, logs_buffer)
        
        # 스케줄링 컨텍스트 생성
        context = SchedulingContext(
            progress_callback=progress_callback,
            debug=debug,
            time_limit_sec=params.get('time_limit_sec', 120.0)
        )
        
        # UI 데이터 변환
        date_plans, global_config, rooms, activities = _convert_ui_data(cfg_ui_optimized, logs_buffer)
        
        if not date_plans:
            return "FAILED", pd.DataFrame(), "날짜별 계획이 없습니다.", 0
        
        # 멀티 날짜 스케줄링 실행
        scheduler = MultiDateScheduler()
        result = scheduler.schedule(
            date_plans=date_plans,
            global_config=global_config,
            rooms=rooms,
            activities=activities,
            context=context  # 컨텍스트 전달
        )
        
        # 결과 분석
        logs_buffer.append(f"=== 스케줄링 결과 ===")
        logs_buffer.append(f"전체 상태: {result.status}")
        logs_buffer.append(f"총 지원자: {result.total_applicants}명")
        logs_buffer.append(f"스케줄된 지원자: {result.scheduled_applicants}명")
        logs_buffer.append(f"성공률: {result.scheduled_applicants/result.total_applicants*100:.1f}%")
        
        if result.status == "SUCCESS":
            # 성공 - UI 형식으로 변환
            final_df = _convert_result_to_ui_format(result, logs_buffer)
            daily_limit = _calculate_daily_limit(result)
            
            return "SUCCESS", final_df, "\n".join(logs_buffer), daily_limit
            
        elif result.status == "PARTIAL":
            # 부분 성공
            logs_buffer.append(f"\n실패한 날짜: {len(result.failed_dates)}개")
            for failed_date in result.failed_dates:
                date_result = result.results[failed_date]
                logs_buffer.append(f"  - {failed_date.date()}: {date_result.error_message}")
            
            final_df = _convert_result_to_ui_format(result, logs_buffer)
            daily_limit = _calculate_daily_limit(result)
            
            return "PARTIAL", final_df, "\n".join(logs_buffer), daily_limit
            
        else:
            # 완전 실패
            logs_buffer.append("\n모든 날짜 스케줄링 실패")
            for failed_date in result.failed_dates:
                date_result = result.results[failed_date]
                logs_buffer.append(f"  - {failed_date.date()}: {date_result.error_message}")
            
            return "FAILED", pd.DataFrame(), "\n".join(logs_buffer), 0
    
    except Exception as e:
        logger.exception("스케줄링 중 예외 발생")
        return "ERROR", pd.DataFrame(), f"예외 발생: {str(e)}", 0


def _apply_smart_integration(cfg_ui: dict, logs_buffer: List[str]) -> dict:
    """
    🚀 스마트 통합 로직: 인접 제약을 자동 감지하여 활동 통합
    
    gap_min=0, adjacent=True인 선후행 제약을 찾아서
    해당 활동들을 자동으로 통합하여 연속성을 보장합니다.
    """
    logs_buffer.append("=== 🚀 스마트 통합 로직 적용 ===")
    
    # 원본 설정 복사
    cfg_optimized = cfg_ui.copy()
    
    # 선후행 제약 확인
    precedence_df = cfg_ui.get("precedence", pd.DataFrame())
    if precedence_df.empty:
        logs_buffer.append("선후행 제약 없음 - 통합 불필요")
        return cfg_optimized
    
    # 인접 제약 찾기 (gap_min=0, adjacent=True)
    adjacent_pairs = []
    for _, rule in precedence_df.iterrows():
        if rule.get("adjacent", False) and rule.get("gap_min", 0) == 0:
            pred = rule["predecessor"]
            succ = rule["successor"]
            adjacent_pairs.append((pred, succ))
            logs_buffer.append(f"🔍 인접 제약 발견: {pred} → {succ} (gap_min=0)")
    
    if not adjacent_pairs:
        logs_buffer.append("gap_min=0 인접 제약 없음 - 통합 불필요")
        return cfg_optimized
    
    # 활동 정보 가져오기
    activities_df = cfg_ui.get("activities", pd.DataFrame()).copy()
    room_plan_df = cfg_ui.get("room_plan", pd.DataFrame()).copy()
    job_acts_map_df = cfg_ui.get("job_acts_map", pd.DataFrame()).copy()
    
    # 각 인접 쌍에 대해 통합 적용
    for pred, succ in adjacent_pairs:
        logs_buffer.append(f"🔧 {pred} + {succ} 통합 적용 중...")
        
        # 활동 정보 찾기
        pred_row = activities_df[activities_df["activity"] == pred]
        succ_row = activities_df[activities_df["activity"] == succ]
        
        if pred_row.empty or succ_row.empty:
            logs_buffer.append(f"⚠️ 활동 정보 없음: {pred} 또는 {succ}")
            continue
        
        pred_info = pred_row.iloc[0]
        succ_info = succ_row.iloc[0]
        
        # 통합 활동 생성
        integrated_name = f"{pred}+{succ}"
        integrated_duration = pred_info["duration_min"] + succ_info["duration_min"]
        integrated_room_type = succ_info["room_type"]  # 후행 활동의 방 사용
        integrated_mode = succ_info["mode"]  # 후행 활동의 모드 사용
        integrated_capacity = succ_info["max_cap"]  # 후행 활동의 용량 사용
        
        logs_buffer.append(f"  → {integrated_name}({integrated_duration}분, {integrated_room_type}, {integrated_mode})")
        
        # 기존 활동 제거
        activities_df = activities_df[~activities_df["activity"].isin([pred, succ])]
        
        # 통합 활동 추가
        new_activity = {
            "use": True,
            "activity": integrated_name,
            "mode": integrated_mode,
            "duration_min": integrated_duration,
            "room_type": integrated_room_type,
            "min_cap": succ_info["min_cap"],
            "max_cap": integrated_capacity
        }
        activities_df = pd.concat([activities_df, pd.DataFrame([new_activity])], ignore_index=True)
        
        # 선후행 제약에서 해당 규칙 제거
        precedence_df = precedence_df[
            ~((precedence_df["predecessor"] == pred) & (precedence_df["successor"] == succ))
        ]
        
        # 지원자 활동 매핑 업데이트
        if pred in job_acts_map_df.columns:
            job_acts_map_df = job_acts_map_df.drop(columns=[pred])
        if succ in job_acts_map_df.columns:
            job_acts_map_df = job_acts_map_df.drop(columns=[succ])
        
        # 통합 활동 추가
        job_acts_map_df[integrated_name] = True
        
        # 방 설정 최적화 (선행 활동 전용 방 제거)
        pred_room_type = pred_info["room_type"]
        if pred_room_type != integrated_room_type:
            pred_count_col = f"{pred_room_type}_count"
            pred_cap_col = f"{pred_room_type}_cap"
            
            if pred_count_col in room_plan_df.columns:
                logs_buffer.append(f"  방 설정 최적화: {pred_room_type} 제거")
                room_plan_df = room_plan_df.drop(columns=[pred_count_col], errors='ignore')
                room_plan_df = room_plan_df.drop(columns=[pred_cap_col], errors='ignore')
    
    # 최적화된 설정 반환
    cfg_optimized["activities"] = activities_df
    cfg_optimized["precedence"] = precedence_df
    cfg_optimized["job_acts_map"] = job_acts_map_df
    cfg_optimized["room_plan"] = room_plan_df
    
    logs_buffer.append(f"✅ 스마트 통합 완료: {len(adjacent_pairs)}개 활동 쌍 통합")
    
    return cfg_optimized


def _convert_ui_data(
    cfg_ui: dict, 
    logs_buffer: List[str]
) -> Tuple[Dict[datetime, DatePlan], GlobalConfig, Dict[str, dict], Dict[str, dict]]:
    """UI 데이터를 새로운 스케줄러 형식으로 변환"""
    
    # 1. 활동 정보 추출
    activities_df = cfg_ui.get("activities", pd.DataFrame())
    if activities_df.empty:
        raise ValueError("활동 정보가 없습니다")
    
    activities = {}
    for _, row in activities_df.iterrows():
        if not row.get("use", False):
            continue
            
        activities[row["activity"]] = {
            "mode": row["mode"],
            "duration_min": int(row["duration_min"]),
            "room_type": row["room_type"],
            "min_capacity": int(row.get("min_cap", 1)),
            "max_capacity": int(row.get("max_cap", 1))
        }
    
    logs_buffer.append(f"활동 {len(activities)}개 로드: {list(activities.keys())}")
    
    # 2. 방 정보 추출  
    room_plan_df = cfg_ui.get("room_plan", pd.DataFrame())
    rooms = {}
    
    if not room_plan_df.empty:
        # room_plan에서 방 타입별 개수와 용량 추출
        for room_type in activities_df["room_type"].dropna().unique():
            count_col = f"{room_type}_count"
            cap_col = f"{room_type}_cap"
            
            if count_col in room_plan_df.columns:
                count = int(room_plan_df[count_col].iloc[0])
                capacity = int(room_plan_df[cap_col].iloc[0]) if cap_col in room_plan_df.columns else 1
                
                rooms[room_type] = {
                    "count": count,
                    "capacity": capacity
                }
    
    logs_buffer.append(f"방 타입 {len(rooms)}개: {rooms}")
    
    # 3. 직무별 활동 매핑
    job_acts_df = cfg_ui.get("job_acts_map", pd.DataFrame())
    
    # 4. 날짜별 계획 생성
    date_plans = {}
    
    # 운영 시간 설정
    oper_window_df = cfg_ui.get("oper_window", pd.DataFrame())
    
    # 멀티 날짜 계획 처리
    multidate_plans = cfg_ui.get("multidate_plans", {})
    
    if multidate_plans:
        # 새로운 멀티 날짜 계획 방식
        logs_buffer.append(f"멀티 날짜 계획 {len(multidate_plans)}개 발견")
        
        for date_key, plan in multidate_plans.items():
            if not plan.get("enabled", True):
                continue  # 비활성화된 날짜는 건너뛰기
            
            plan_date = plan["date"]
            if isinstance(plan_date, str):
                plan_date = datetime.strptime(plan_date, "%Y-%m-%d")
            elif hasattr(plan_date, 'date'):
                plan_date = datetime.combine(plan_date, datetime.min.time())
            else:
                plan_date = datetime.combine(plan_date, datetime.min.time())
            
            # 해당 날짜의 직무별 인원수
            jobs = {}
            for job in plan.get("jobs", []):
                jobs[job["code"]] = int(job["count"])
            
            # 해당 직무가 수행할 활동들 (기본적으로 모든 활동)
            selected_activities = list(activities.keys())
            
            date_plans[plan_date] = DatePlan(
                date=plan_date,
                jobs=jobs,
                selected_activities=selected_activities
            )
            
            logs_buffer.append(f"날짜 계획 생성: {plan_date.date()}, 직무: {jobs}, 활동: {selected_activities}")
            
    elif not job_acts_df.empty:
        # 기존 방식 (하위 호환성)
        logs_buffer.append("기존 job_acts_map 방식 사용")
        
        # UI에서 선택한 날짜들 가져오기
        selected_dates = cfg_ui.get("interview_dates", [cfg_ui.get("interview_date")])
        if not selected_dates or selected_dates == [None]:
            # 기본값: 내일 날짜
            selected_dates = [(datetime.now() + timedelta(days=1)).date()]
        
        # 각 날짜별로 DatePlan 생성
        for _, row in job_acts_df.iterrows():
            # 직무별 인원수
            jobs = {row["code"]: int(row["count"])}
            
            # 해당 직무가 수행할 활동들
            selected_activities = []
            for activity_name in activities.keys():
                if row.get(activity_name, False):
                    selected_activities.append(activity_name)
            
            # 각 선택된 날짜별로 DatePlan 생성
            for selected_date in selected_dates:
                if isinstance(selected_date, str):
                    plan_date = datetime.strptime(selected_date, "%Y-%m-%d")
                elif hasattr(selected_date, 'date'):
                    plan_date = datetime.combine(selected_date, datetime.min.time())
                else:
                    plan_date = datetime.combine(selected_date, datetime.min.time())
                
                date_plans[plan_date] = DatePlan(
                    date=plan_date,
                    jobs=jobs,
                    selected_activities=selected_activities
                )
                
                logs_buffer.append(f"날짜 계획 생성: {plan_date.date()}, 직무: {jobs}, 활동: {selected_activities}")
            break  # 첫 번째 직무 행만 처리 (모든 날짜에 동일 적용)
    
    # 5. 선후행 제약 추출
    precedence_df = cfg_ui.get("precedence", pd.DataFrame())
    precedence_rules = []
    
    if not precedence_df.empty:
        for _, row in precedence_df.iterrows():
            if row["predecessor"] != "__START__" and row["successor"] != "__END__":
                precedence_rules.append(PrecedenceRule(
                    predecessor=row["predecessor"],
                    successor=row["successor"],
                    gap_min=int(row.get("gap_min", 5))
                ))
    
    # 6. 글로벌 설정
    operating_hours = {"default": (time(9, 0), time(18, 0))}
    if not oper_window_df.empty:
        start_str = oper_window_df["start_time"].iloc[0]
        end_str = oper_window_df["end_time"].iloc[0]
        
        if isinstance(start_str, str):
            start_time = datetime.strptime(start_str, "%H:%M").time()
        else:
            start_time = start_str
            
        if isinstance(end_str, str):
            end_time = datetime.strptime(end_str, "%H:%M").time()
        else:
            end_time = end_str
            
        operating_hours["default"] = (start_time, end_time)
    
    # Batched 그룹 크기 설정
    batched_group_sizes = {}
    for activity_name, activity_info in activities.items():
        if activity_info["mode"] == "batched":
            batched_group_sizes[activity_name] = (
                activity_info["min_capacity"],
                activity_info["max_capacity"]
            )
    
    global_config = GlobalConfig(
        operating_hours=operating_hours,
        precedence_rules=precedence_rules,
        batched_group_sizes=batched_group_sizes,
        room_settings={},
        time_settings={},
        global_gap_min=cfg_ui.get('global_gap_min', 5),
        max_stay_hours=cfg_ui.get('max_stay_hours', 5)  # 기본값을 5시간으로 변경
    )
    
    return date_plans, global_config, rooms, activities


def _convert_result_to_ui_format(result, logs_buffer: List[str]) -> pd.DataFrame:
    """스케줄링 결과를 UI 표시용 DataFrame으로 변환"""
    
    schedule_data = []
    
    for date, date_result in result.results.items():
        if date_result.status != "SUCCESS":
            continue
            
        for item in date_result.schedule:
            # 더미 지원자는 제외
            if item.applicant_id.startswith("DUMMY_"):
                continue
                
            schedule_data.append({
                "interview_date": date,
                "applicant_id": item.applicant_id,
                "job_code": item.job_code,
                "activity_name": item.activity_name,
                "room_name": item.room_name,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "duration_min": int((item.end_time - item.start_time).total_seconds() / 60)
            })
    
    if not schedule_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(schedule_data)
    
    # 시간 순으로 정렬
    df = df.sort_values(["interview_date", "start_time", "applicant_id"])
    
    logs_buffer.append(f"UI 형식 변환 완료: {len(df)}개 스케줄 항목")
    
    return df


def _calculate_daily_limit(result) -> int:
    """일일 처리 가능 인원 계산"""
    max_daily = 0
    
    for date, date_result in result.results.items():
        if date_result.status == "SUCCESS":
            daily_count = len([
                item for item in date_result.schedule 
                if not item.applicant_id.startswith("DUMMY_")
            ])
            max_daily = max(max_daily, daily_count)
    
    return max_daily


def get_scheduler_comparison() -> Dict[str, Any]:
    """두 스케줄러 시스템의 비교 정보 제공"""
    return {
        "legacy": {
            "name": "OR-Tools 기반 스케줄러",
            "description": "Google OR-Tools CP-SAT 제약 해결사 사용",
            "pros": ["강력한 제약 해결", "최적해 보장"],
            "cons": ["설정 복잡", "큰 문제에서 느림"],
            "suitable_for": "소규모, 복잡한 제약"
        },
        "new": {
            "name": "계층적 스케줄러 v2",
            "description": "3단계 계층적 분해 + 휴리스틱 방식",
            "pros": ["빠른 처리", "대규모 처리", "직관적 설정", "Batched 활동 지원"],
            "cons": ["최적해 미보장"],
            "suitable_for": "대규모, 실시간 처리"
        }
    }


# 기존 인터페이스와의 호환성을 위한 함수
def solve_for_days_hybrid(
    cfg_ui: dict, 
    params: dict = None, 
    debug: bool = False,
    use_new_scheduler: bool = True
) -> Tuple[str, pd.DataFrame, str, int]:
    """
    두 스케줄러 중 선택하여 실행
    """
    if use_new_scheduler:
        return solve_for_days_v2(cfg_ui, params, debug)
    else:
        # 기존 스케줄러 사용
        from .solver import solve_for_days
        return solve_for_days(cfg_ui, params, debug)


def solve_for_days_optimized(
    cfg_ui: dict, 
    params: dict = None, 
    debug: bool = False,
    progress_callback: Optional[ProgressCallback] = None,
    optimization_config: Optional[Dict] = None
) -> Tuple[str, pd.DataFrame, str, int]:
    """
    최적화된 스케줄러를 사용하여 UI 요청 처리
    대규모 처리에 특화된 성능 최적화 버전
    
    Args:
        cfg_ui: UI 설정 딕셔너리
        params: 추가 파라미터
        debug: 디버그 모드
        progress_callback: 실시간 진행 상황 콜백 함수
        optimization_config: 최적화 설정
    
    Returns:
        (status, final_wide_df, logs, daily_limit)
    """
    try:
        # 로깅 설정
        log_level = logging.DEBUG if debug else logging.WARNING
        logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
        logger = logging.getLogger(__name__)
        
        logs_buffer = []
        
        # 최적화 설정 처리
        from .optimized_scheduler import OptimizationConfig
        
        if optimization_config:
            opt_config = OptimizationConfig(
                enable_parallel_processing=optimization_config.get("enable_parallel_processing", True),
                enable_memory_optimization=optimization_config.get("enable_memory_optimization", True),
                enable_caching=optimization_config.get("enable_caching", True),
                max_workers=optimization_config.get("max_workers"),
                chunk_size_threshold=optimization_config.get("chunk_size_threshold", 100),
                memory_cleanup_interval=optimization_config.get("memory_cleanup_interval", 50)
            )
        else:
            opt_config = OptimizationConfig()
        
        # 스케줄링 컨텍스트 생성
        context = SchedulingContext(
            progress_callback=progress_callback,
            enable_detailed_logging=debug,
            real_time_updates=True
        )
        
        # UI 데이터 변환
        date_plans, global_config, rooms, activities = _convert_ui_data(cfg_ui, logs_buffer)
        
        if not date_plans:
            return "FAILED", pd.DataFrame(), "날짜별 계획이 없습니다.", 0
        
        # 멀티 날짜 스케줄링 실행 (최적화된 스케줄러 사용)
        from .optimized_multi_date_scheduler import OptimizedMultiDateScheduler
        
        scheduler = OptimizedMultiDateScheduler(optimization_config=opt_config)
        result = scheduler.schedule(
            date_plans=date_plans,
            global_config=global_config,
            rooms=rooms,
            activities=activities,
            context=context
        )
        
        # 결과 분석
        logs_buffer.append(f"=== 최적화된 스케줄링 결과 ===")
        logs_buffer.append(f"전체 상태: {result.status}")
        logs_buffer.append(f"총 지원자: {result.total_applicants}명")
        logs_buffer.append(f"스케줄된 지원자: {result.scheduled_applicants}명")
        logs_buffer.append(f"성공률: {result.scheduled_applicants/result.total_applicants*100:.1f}%")
        
        if hasattr(scheduler, 'stats'):
            stats = scheduler.get_overall_stats()
            logs_buffer.append(f"최적화 통계: 캐시 적중률 {stats.get('cache_hit_rate', 0):.1f}%, "
                             f"병렬 작업 {stats.get('parallel_tasks', 0)}개")
        
        if result.status == "SUCCESS":
            # 성공 - UI 형식으로 변환
            final_df = _convert_result_to_ui_format(result, logs_buffer)
            daily_limit = _calculate_daily_limit(result)
            
            return "SUCCESS", final_df, "\n".join(logs_buffer), daily_limit
            
        elif result.status == "PARTIAL":
            # 부분 성공
            logs_buffer.append(f"\n실패한 날짜: {len(result.failed_dates)}개")
            for failed_date in result.failed_dates:
                date_result = result.results[failed_date]
                logs_buffer.append(f"  - {failed_date.date()}: {date_result.error_message}")
            
            final_df = _convert_result_to_ui_format(result, logs_buffer)
            daily_limit = _calculate_daily_limit(result)
            
            return "PARTIAL", final_df, "\n".join(logs_buffer), daily_limit
            
        else:
            # 완전 실패
            logs_buffer.append("\n모든 날짜 스케줄링 실패")
            for failed_date in result.failed_dates:
                date_result = result.results[failed_date]
                logs_buffer.append(f"  - {failed_date.date()}: {date_result.error_message}")
            
            return "FAILED", pd.DataFrame(), "\n".join(logs_buffer), 0
    
    except Exception as e:
        logger.exception("최적화된 스케줄링 중 예외 발생")
        return "ERROR", pd.DataFrame(), f"예외 발생: {str(e)}", 0


def solve_for_days_two_phase(
    cfg_ui: dict, 
    params: dict = None, 
    debug: bool = False,
    progress_callback: Optional[ProgressCallback] = None,
    percentile: float = 90.0
) -> Tuple[str, pd.DataFrame, str, int, Dict[str, pd.DataFrame]]:
    """
    2단계 하드 제약 스케줄링
    
    Args:
        cfg_ui: UI 설정 딕셔너리
        params: 추가 파라미터
        debug: 디버그 모드
        progress_callback: 실시간 진행 상황 콜백 함수
        percentile: 하드 제약 계산용 분위수 (기본값: 90.0)
    
    Returns:
        (status, final_wide_df, logs, daily_limit, reports)
    """
    try:
        # 로깅 설정
        log_level = logging.DEBUG if debug else logging.WARNING
        logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
        logger = logging.getLogger(__name__)
        
        logs_buffer = []
        
        # 2단계 하드 제약 스케줄러 실행
        from .hard_constraint_scheduler import HardConstraintScheduler
        
        scheduler = HardConstraintScheduler(percentile=percentile)
        result = scheduler.run_two_phase_scheduling(
            cfg_ui=cfg_ui,
            params=params,
            debug=debug,
            progress_callback=progress_callback
        )
        
        # 결과 분석
        logs_buffer.append(f"=== 2단계 하드 제약 스케줄링 결과 ===")
        logs_buffer.append(f"전체 상태: {result['status']}")
        
        if result['status'] == "SUCCESS":
            # 성공 - UI 형식으로 변환
            final_df = result['phase2_result']
            
            # 일일 처리 가능 인원 계산
            if not final_df.empty:
                daily_limit = final_df.groupby('interview_date')['applicant_id'].nunique().max()
            else:
                daily_limit = 0
            
            # 종합 리포트 생성
            reports = scheduler.generate_comprehensive_report(result)
            
            return "SUCCESS", final_df, "\n".join(logs_buffer), daily_limit, reports
            
        elif result['status'] == "PHASE1_FAILED":
            logs_buffer.append(f"1단계 스케줄링 실패: {result['error']}")
            return "FAILED", pd.DataFrame(), "\n".join(logs_buffer), 0, {}
            
        elif result['status'] == "ANALYSIS_FAILED":
            logs_buffer.append(f"체류시간 분석 실패: {result['error']}")
            return "FAILED", pd.DataFrame(), "\n".join(logs_buffer), 0, {}
            
        elif result['status'] == "PHASE2_FAILED":
            logs_buffer.append(f"2단계 스케줄링 실패: {result['error']}")
            # 1단계 결과라도 반환
            final_df = result['phase1_result']
            if not final_df.empty:
                daily_limit = final_df.groupby('interview_date')['applicant_id'].nunique().max()
            else:
                daily_limit = 0
            
            reports = {}
            if result.get('constraint_analysis'):
                reports['constraint_analysis'] = result['constraint_analysis']
            
            return "PARTIAL", final_df, "\n".join(logs_buffer), daily_limit, reports
            
        else:
            logs_buffer.append(f"알 수 없는 상태: {result['status']}")
            return "FAILED", pd.DataFrame(), "\n".join(logs_buffer), 0, {}
    
    except Exception as e:
        logger.exception("2단계 하드 제약 스케줄링 중 예외 발생")
        return "ERROR", pd.DataFrame(), f"예외 발생: {str(e)}", 0, {} 