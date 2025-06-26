# solver/solver.py  –  UI 데이터만으로 OR-Tools 실행
from datetime import timedelta, datetime
import pandas as pd
import traceback, sys, streamlit as st
from interview_opt_test_v4 import build_model
import contextlib, io
from pathlib import Path
import string
from .three_stage_optimizer import solve_with_three_stages



def _derive_internal_tables(cfg_ui: dict, the_date: pd.Timestamp, *, debug: bool = False) -> dict:
    """
    Streamlit UI 값으로부터 build_model 이 바로 쓸 4개 표를 생성.
    debug=True 이면 브라우저에 cfg_map / cfg_avail 미리보기 출력.
    """
    import pandas as pd
    import streamlit as st

    # ① 활동 ↔ 소요시간 ----------------------------
    cfg_duration = cfg_ui["activities"][["activity", "duration_min"]].copy()

    # ▶ room_type 목록을 Activities 표에서 자동 추출
    room_types_ui = cfg_ui["activities"]["room_type"].dropna().unique()

    # ② 활동 ↔ loc(room_type) ----------------------
    base_map = cfg_ui["activities"][["activity", "room_type"]]

    if "space_avail" in cfg_ui and not cfg_ui["space_avail"].empty:
        sa = cfg_ui["space_avail"]
        rows = [
            {"activity": act, "loc": loc}
            for _, row in base_map.iterrows()
            for act, base in [(row["activity"], row["room_type"])]
            for loc in sa["loc"].unique()
            if str(loc).startswith(base)
        ]
        cfg_map = pd.DataFrame(rows)
    else:
        rp, rows = cfg_ui["room_plan"], []
        for _, r in rp.iterrows():
            for base in room_types_ui:
                n = int(r.get(f"{base}_count", 0))
                if n == 0:
                    continue
                for i in range(1, n + 1):
                    if n > 1:
                        suffix = string.ascii_uppercase[i-1]
                        loc = f"{base}{suffix}"
                    else:
                        loc = base
                    rows.append({"room_type": base, "loc": loc})
        
        exploded = pd.DataFrame(rows, columns=['room_type', 'loc']).drop_duplicates("loc") if rows else pd.DataFrame(columns=['room_type', 'loc'])

        cfg_map = (
            base_map.merge(exploded, on="room_type", how="left")
                    .drop(columns=["room_type"])
        )
        if cfg_map['loc'].isnull().any():
            failed_acts = cfg_map[cfg_map['loc'].isnull()]['activity'].unique().tolist()
            st.error(f"**설정 오류:** 다음 활동에 할당된 장소(Room Type)를 'Room Plan'에서 찾을 수 없습니다: **`{', '.join(failed_acts)}`**. 'Activities' 페이지와 'Room Plan' 페이지의 Room Type 이름이 정확히 일치하는지 확인해주세요. (예: '심층면접실'은 동일해야 함)")
            st.stop()

    # ③ 날짜·방별 capacity --------------------------
    if "space_avail" in cfg_ui and not cfg_ui["space_avail"].empty:
        cfg_avail = cfg_ui["space_avail"][["loc", "date", "capacity_max"]].copy()
        cfg_avail["capacity_override"] = pd.NA
    else:
        rp, rows = cfg_ui["room_plan"], []
        for _, r in rp.iterrows():
            date = pd.to_datetime(r["date"])
            for base in room_types_ui:
                n   = int(r.get(f"{base}_count", 0))
                if n == 0:
                    continue
                cap = int(r.get(f"{base}_cap", 1))
                for i in range(1, n + 1):
                    if n > 1:
                        suffix = string.ascii_uppercase[i-1]
                        loc = f"{base}{suffix}"
                    else:
                        loc = base
                    rows.append(
                        {"loc": loc, "date": date,
                         "capacity_max": cap, "capacity_override": pd.NA}
                    )
        cfg_avail = pd.DataFrame(rows)

    # ④ 전형(code) × 날짜별 운영시간 -----------------
    raw_oper = cfg_ui["oper_window"].copy()
    for old, new in [("start", "start_time"), ("end", "end_time")]:
        if old in raw_oper.columns and new in raw_oper.columns:
            raw_oper = raw_oper.drop(columns=[old])
    cfg_oper = (
        raw_oper.dropna(subset=["code", "date",
                                "start" if "start" in raw_oper.columns else "start_time",
                                "end"   if "end"   in raw_oper.columns else "end_time"])
                .query("code != ''")
                .drop_duplicates(["code", "date"])
                .reset_index(drop=True)
                .rename(columns={"start": "start_time", "end": "end_time"})
    )
    cfg_oper["date"] = pd.to_datetime(cfg_oper["date"])
    cfg_oper["start_time"] = cfg_oper["start_time"].astype(str)
    cfg_oper["end_time"]   = cfg_oper["end_time"].astype(str)

    # ────── 🔎  디버그 미리보기 (브라우저) ──────
    if debug:
        st.markdown("---")
        st.markdown(f"### 🐞 디버그 정보 (처리 날짜: {the_date.date()})")
        st.markdown("#### `cfg_map` (activity ↔ loc) – 상위 20행")
        st.dataframe(cfg_map.sort_values(["activity", "loc"]).head(20),
                     use_container_width=True)

        st.markdown("#### `cfg_avail` – 상위 20행")
        cfg_avail_today = cfg_avail[cfg_avail['date'] == the_date]
        
        if not cfg_avail_today.empty:
            st.dataframe(cfg_avail_today.sort_values("loc").head(20),
                     use_container_width=True)
        else:
            st.markdown(f"**경고:** `{the_date.date()}`에 해당하는 장소(Room) 정보가 'Room Plan'에 없습니다.")

        st.markdown("---")

    # 결과 반환 --------------------------------------
    return dict(
        cfg_duration=cfg_duration,
        cfg_map=cfg_map,
        cfg_avail=cfg_avail,
        cfg_oper=cfg_oper,
        group_meta=cfg_ui["activities"].copy(),
    )

def generate_virtual_candidates(job_acts_map: pd.DataFrame) -> pd.DataFrame:
    """'직무별 면접활동' 설정으로부터 가상 지원자 목록을 생성합니다."""
    all_candidates = []
    for _, row in job_acts_map.iterrows():
        code = row['code']
        count = int(row['count'])
        activities = [act for act, required in row.items() if act not in ['code', 'count'] and required]
        
        for i in range(1, count + 1):
            candidate_id = f"{code}_{str(i).zfill(3)}"
            for act in activities:
                all_candidates.append({'id': candidate_id, 'code': code, 'activity': act})
    
    if not all_candidates:
        return pd.DataFrame(columns=['id', 'code', 'activity'])

    return pd.DataFrame(all_candidates)

def _calculate_dynamic_daily_limit(
    room_plan_tpl: pd.DataFrame, 
    oper_window_tpl: pd.DataFrame, 
    activities_df: pd.DataFrame, 
    job_acts_map: pd.DataFrame,
    precedence_df: pd.DataFrame = None  # 추가: 선후행 제약 정보
) -> int:
    """사용 가능한 자원(시간, 공간)과 지원자별 필요 자원을 기반으로 일일 처리 가능 인원을 동적으로 추정합니다."""
    from datetime import date, datetime
    
    # 1. 총 가용 시간 계산
    start_time_str = oper_window_tpl['start_time'].iloc[0]
    end_time_str = oper_window_tpl['end_time'].iloc[0]

    if isinstance(start_time_str, str):
        start_time = pd.to_datetime(start_time_str).time()
    else:
        start_time = start_time_str

    if isinstance(end_time_str, str):
        end_time = pd.to_datetime(end_time_str).time()
    else:
        end_time = end_time_str

    if not start_time or not end_time:
        return 20 # Fallback

    total_oper_minutes = (datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)).total_seconds() / 60
    
    room_types = activities_df.query("use==True")['room_type'].dropna().unique()
    total_room_minutes = 0
    for rt in room_types:
        count_col = f"{rt}_count"
        if count_col in room_plan_tpl:
            try:
                num_rooms = pd.to_numeric(room_plan_tpl[count_col].iloc[0], errors='coerce')
                if pd.notna(num_rooms):
                    total_room_minutes += num_rooms * total_oper_minutes
            except (ValueError, IndexError):
                pass
            
    if total_room_minutes <= 0:
        return 20

    # 2. 지원자 1명당 평균 필요 시간 계산
    job_acts_map_copy = job_acts_map.copy()
    
    if 'total_duration' not in job_acts_map_copy.columns:
        job_acts_map_copy['total_duration'] = 0
        for idx, row in job_acts_map_copy.iterrows():
            total_duration = 0
            activities = [act for act, required in row.items() if required and act not in ['code', 'count', 'total_duration']]
            
            for act_name in activities:
                act_info = activities_df[activities_df['activity'] == act_name]
                if not act_info.empty:
                    duration = act_info['duration_min'].iloc[0]
                    total_duration += duration
            job_acts_map_copy.loc[idx, 'total_duration'] = total_duration

    total_applicants = job_acts_map_copy['count'].sum()
    if total_applicants == 0:
        return 20
        
    weighted_avg_duration = (job_acts_map_copy['total_duration'] * job_acts_map_copy['count']).sum() / total_applicants
    
    if weighted_avg_duration <= 0:
        return 20

    # 3. 일일 처리 가능 인원 추산 (안전 마진 80% 적용)
    daily_capacity = int((total_room_minutes / weighted_avg_duration) * 0.8)
    
    # 3-1. batched 모드가 있을 때 추가 제약 고려
    if 'mode' in activities_df.columns:
        batched_acts = activities_df[activities_df['mode'] == 'batched']
        if not batched_acts.empty:
            # batched 활동의 병목 계산
            group_size = int(batched_acts.iloc[0]['max_cap'])
            
            # Adjacent 제약이 있는 batched → parallel → individual 흐름 감지
            has_complex_adjacent = False
            if precedence_df is not None and not precedence_df.empty and 'adjacent' in precedence_df.columns:
                # batched → parallel/individual adjacent 체인 확인
                for _, rule in precedence_df.iterrows():
                    if rule.get('adjacent', False):
                        pred = rule['predecessor']
                        succ = rule['successor']
                        
                        pred_act = activities_df[activities_df['activity'] == pred]
                        succ_act = activities_df[activities_df['activity'] == succ]
                        
                        if not pred_act.empty and not succ_act.empty:
                            pred_mode = pred_act.iloc[0].get('mode', 'individual')
                            succ_mode = succ_act.iloc[0].get('mode', 'individual')
                            pred_cap = int(pred_act.iloc[0].get('max_cap', 1))
                            succ_cap = int(succ_act.iloc[0].get('max_cap', 1))
                            
                            # 진짜 문제가 되는 경우만 감지
                            # 1. Batched → Individual adjacent (그룹 크기 > individual 방 수)
                            if pred_mode == 'batched' and succ_mode == 'individual':
                                succ_room_type = succ_act.iloc[0]['room_type']
                                count_col = f"{succ_room_type}_count"
                                if count_col in room_plan_tpl.columns:
                                    succ_room_count = int(room_plan_tpl[count_col].iloc[0])
                                    if group_size > succ_room_count:
                                        has_complex_adjacent = True
                                        break
                            # 2. Parallel → Individual adjacent (parallel 용량 > individual 방 수)
                            elif pred_mode == 'parallel' and succ_mode == 'individual':
                                succ_room_type = succ_act.iloc[0]['room_type']
                                count_col = f"{succ_room_type}_count"
                                if count_col in room_plan_tpl.columns:
                                    succ_room_count = int(room_plan_tpl[count_col].iloc[0])
                                    # 발표준비(2명) → 발표면접(2개 방)은 OK
                                    if pred_cap > succ_room_count:
                                        has_complex_adjacent = True
                                        break
            
            bottlenecks = []
            for _, act in activities_df.iterrows():
                if not act['use']:
                    continue
                    
                room_type = act['room_type']
                duration = act['duration_min']
                mode = act.get('mode', 'individual')
                
                # 방 개수 가져오기
                count_col = f"{room_type}_count"
                if count_col in room_plan_tpl.columns:
                    room_count = int(room_plan_tpl[count_col].iloc[0])
                    room_cap = int(room_plan_tpl.get(f"{room_type}_cap", 1).iloc[0])
                    
                    # 하루 동안 처리 가능한 슬롯 수
                    slots_per_day = int(total_oper_minutes // duration)
                    
                    if mode == 'batched':
                        # batched: 그룹 단위로 처리
                        groups_per_slot = room_count  # 각 방에 1그룹씩
                        max_groups_per_day = slots_per_day * groups_per_slot
                        max_people_per_day = max_groups_per_day * group_size
                    elif mode == 'parallel':
                        # parallel: 방 용량만큼 동시 처리
                        max_people_per_day = slots_per_day * room_count * room_cap
                    else:  # individual
                        # individual: 1명씩 처리
                        max_people_per_day = slots_per_day * room_count
                    
                    bottlenecks.append(max_people_per_day)
            
            # 가장 작은 병목을 기준으로 조정
            if bottlenecks:
                batched_capacity = int(min(bottlenecks) * 0.8)
                
                # Adjacent 제약이 있는 복잡한 흐름이면 추가로 20% 감소 (50%는 너무 과도함)
                if has_complex_adjacent:
                    batched_capacity = int(batched_capacity * 0.8)
                    
                # 그룹 크기의 배수로 조정 (batched → parallel → individual 흐름 최적화)
                # 하루에 처리할 수 있는 완전한 그룹 수만 허용
                if group_size > 0:
                    complete_groups = batched_capacity // group_size
                    # 최소값 제한 없이 계산된 그룹 수 사용
                    if complete_groups < 1:
                        complete_groups = 1  # 최소 1개 그룹은 보장
                    batched_capacity = complete_groups * group_size
                    
                daily_capacity = min(daily_capacity, batched_capacity)
    
    return max(10, daily_capacity)

def solve_for_days(cfg_ui: dict, params: dict, debug: bool):
    """
    최소 운영일을 추정하기 위한 메인 솔버 함수.
    Day 1부터 시작하여 모든 지원자가 배정될 때까지 날짜를 늘려가며 시도.
    batched 모드가 있으면 3단계 최적화를 수행.
    """
    logger = st.logger.get_logger("solver")
    
    # 1. 가상 지원자 생성
    job_acts_map = cfg_ui.get("job_acts_map")
    if job_acts_map is None or job_acts_map.empty:
        st.error("⛔ '② 직무별 면접활동'에서 인원수 설정을 먼저 완료해주세요.")
        return "NO_JOB_DATA", None, "직무별 인원 정보 없음", 0
        
    candidates_df = generate_virtual_candidates(job_acts_map)
    if candidates_df.empty:
        st.info("처리할 지원자 데이터가 없습니다.")
        return "NO_CANDIDATES", None, "지원자 없음", 0
    
    # 디버그 헬퍼 초기화 (candidates_df가 생성된 후)
    debug_helper = None
    if debug:
        from utils.debug_helper import SchedulingDebugHelper
        debug_helper = SchedulingDebugHelper()
        debug_log_file = debug_helper.start_session(cfg_ui)
        logger.info(f"디버그 로그 파일: {debug_log_file}")
        debug_helper.log("INFO", "스케줄링 시작", {"total_candidates": len(candidates_df)})

    # 2. 고정 설정값 준비 (템플릿)
    room_plan_tpl = cfg_ui.get("room_plan")
    oper_window_tpl = cfg_ui.get("oper_window")
    activities_df = cfg_ui.get("activities")
    rules = cfg_ui.get('precedence', pd.DataFrame())
    
    if room_plan_tpl is None or room_plan_tpl.empty:
        st.error("⛔ '③ 운영공간설정'에서 공간 템플릿 설정을 먼저 완료해주세요.")
        return "NO_ROOM_PLAN", None, "운영 공간 템플릿 없음", 0
    if oper_window_tpl is None or oper_window_tpl.empty:
        st.error("⛔ '④ 운영시간설정'에서 시간 템플릿 설정을 먼저 완료해주세요.")
        return "NO_OPER_WINDOW", None, "운영 시간 템플릿 없음", 0

    # +++ 동적 일일 처리량 계산 +++
    daily_candidate_limit = 0
    try:
        daily_candidate_limit = _calculate_dynamic_daily_limit(
            room_plan_tpl=room_plan_tpl,
            oper_window_tpl=oper_window_tpl,
            activities_df=activities_df.query("use==True"),
            job_acts_map=job_acts_map,
            precedence_df=rules
        )
    except Exception as e:
        logger.warning(f"동적 일일 처리량 계산 실패: {e}. 기본값(70)으로 대체합니다.")
        daily_candidate_limit = 70
    # ++++++++++++++++++++++++++++++
    
    # batched 모드 확인
    has_batched = False
    if 'mode' in activities_df.columns:
        has_batched = any(activities_df['mode'] == 'batched')
    
    if has_batched:
        log_messages = ["집단면접(batched) 모드가 감지되어 3단계 최적화를 수행합니다."]
    else:
        log_messages = []

    # 3. 날짜를 늘려가며 스케줄링 시도
    all_scheduled_cands_long = pd.DataFrame()
    
    max_days = 30
    all_scheduled_ids = set()
    
    # 전체 그룹 정보 누적
    all_group_info = {
        'member_to_group': {},
        'group_sizes': {}
    }
    
    for day_num in range(1, max_days + 1):
        the_date = pd.to_datetime("2025-01-01") + timedelta(days=day_num - 1)

        unscheduled_cands = candidates_df[~candidates_df['id'].isin(all_scheduled_ids)]
        if unscheduled_cands.empty:
            log_messages.append("✅ 모든 지원자 배정 완료. 시뮬레이션을 종료합니다.")
            break

        candidate_ids_for_day = unscheduled_cands['id'].unique()[:daily_candidate_limit]
        cands_to_schedule_df = unscheduled_cands[unscheduled_cands['id'].isin(candidate_ids_for_day)]

        candidate_info = {
            cid: {'job_code': group['code'].iloc[0], 'activities': group['activity'].tolist()}
            for cid, group in cands_to_schedule_df.groupby('id')
        }

        room_types = activities_df.query("use==True")['room_type'].dropna().unique()
        room_info_list = []
        for rt in room_types:
            count = int(room_plan_tpl.get(f"{rt}_count", 0).iloc[0])
            cap = int(room_plan_tpl.get(f"{rt}_cap", 1).iloc[0])
            
            if count == 1:
                room_info_list.append({'loc': rt, 'capacity': cap})
            else:
                # 여러 개인 경우 알파벳 접미사 사용 (A, B, C...)
                for i in range(count):
                    suffix = string.ascii_uppercase[i]
                    loc = f"{rt}{suffix}"
                    room_info_list.append({'loc': loc, 'capacity': cap})
                    
        room_info = {row['loc']: {'capacity': row['capacity']} for row in room_info_list}

        act_info = {
            row['activity']: {
                'duration': int(row['duration_min']),
                'required_rooms': [row['room_type']]
            }
            for _, row in activities_df.iterrows() if row['use']
        }
        
        base_time = pd.to_datetime('00:00:00').time()
        start_time_str = oper_window_tpl['start_time'].iloc[0]
        end_time_str = oper_window_tpl['end_time'].iloc[0]
        
        start_dt = datetime.combine(the_date.date(), pd.to_datetime(start_time_str).time())
        end_dt = datetime.combine(the_date.date(), pd.to_datetime(end_time_str).time())
        start_minutes = int((start_dt - datetime.combine(the_date.date(), base_time)).total_seconds() / 60)
        end_minutes = int((end_dt - datetime.combine(the_date.date(), base_time)).total_seconds() / 60)
        
        oper_hours = {code: (start_minutes, end_minutes) for code in job_acts_map['code'].unique()}
        
        config = {
            'the_date': the_date,
            'min_gap_min': params.get('min_gap_min', 5),
            'act_info': act_info,
            'candidate_info': candidate_info,
            'room_info': room_info,
            'oper_hours': oper_hours,
            'rules': [tuple(x) for x in rules.to_records(index=False)],
            'debug_mode': debug,
            'num_cpus': params.get('num_cpus', 8),
            'optimize_for_max_scheduled': True,
            'time_limit_sec': 60.0
        }
        
        log_messages.append(f"--- Day {day_num} ({the_date.date()}) ---")
        log_messages.append(f"일일 최대 처리 가능 인원: {daily_candidate_limit}명")
        log_messages.append(f"시도 대상 지원자 수: {len(candidate_info)}")

        # batched 모드가 있으면 3단계 최적화 사용
        if has_batched:
            log_messages.append(f"Batched 모드 감지 - 3단계 최적화 사용")
            # 3단계 최적화를 위한 추가 파라미터 설정
            cfg_ui_day = cfg_ui.copy()
            cfg_ui_day['candidates_for_day'] = cands_to_schedule_df
            
            result = solve_with_three_stages(
                cfg_ui_day, params, the_date, cands_to_schedule_df, debug
            )
            
            log_messages.append(f"3단계 최적화 결과 길이: {len(result)}")
            
            # 3-stage optimizer가 4개의 값을 반환하는 경우와 3개를 반환하는 경우 모두 처리
            if len(result) == 4:
                status, wide_df, stage_logs, group_info = result
                log_messages.append(f"그룹 정보 반환됨: {group_info is not None}")
                if group_info is not None:
                    log_messages.append(f"  - member_to_group 크기: {len(group_info.get('member_to_group', {}))}")
                    log_messages.append(f"  - group_sizes 크기: {len(group_info.get('group_sizes', {}))}")
                
                # 이번 날짜의 그룹 정보를 전체 그룹 정보에 누적
                if group_info and group_info.get('member_to_group'):
                    # 그룹 번호 오프셋 계산 (기존 그룹 수 + 1부터 시작)
                    existing_groups = max(all_group_info['group_sizes'].keys()) if all_group_info['group_sizes'] else 0
                    
                    # member_to_group 업데이트 (그룹 번호 조정)
                    for member, group_num in group_info.get('member_to_group', {}).items():
                        all_group_info['member_to_group'][member] = group_num + existing_groups
                    
                    # group_sizes 업데이트 (그룹 번호 조정)
                    for group_num, size in group_info.get('group_sizes', {}).items():
                        all_group_info['group_sizes'][group_num + existing_groups] = size
                        
                    log_messages.append(f"Day {day_num}: {len(group_info.get('member_to_group', {}))}명의 그룹 정보 추가됨")
                else:
                    log_messages.append(f"Day {day_num}: 그룹 정보가 비어있거나 None")
            else:
                status, wide_df, stage_logs = result
                log_messages.append(f"3단계 최적화가 그룹 정보를 반환하지 않음 (3개 값만 반환)")
            
            if isinstance(stage_logs, list):
                build_model_logs = stage_logs
            else:
                build_model_logs = [stage_logs]
                
            # 3단계 최적화가 실패한 경우
            if status not in ["OK", "OPTIMAL", "FEASIBLE"] or wide_df is None:
                log_messages.append(f"⚠️ 3단계 최적화 실패 (상태: {status})")
                log_messages.append("❌ Batched 활동이 있지만 3단계 최적화가 실패했습니다.")
                log_messages.append("   이 경우 올바른 그룹 스케줄링이 불가능합니다.")
                
                # Batched 모드에서는 반드시 3단계 최적화가 성공해야 함
                # 기존 방식으로 폴백하지 않고 실패 처리
                log_messages.append("   → 이 날짜는 스케줄링을 건너뜁니다.")
                continue  # 다음 날짜로
        else:
            # 기존 방식 사용
            model, status, wide_df, build_model_logs = build_model(config, logger)
        
        if build_model_logs:
            log_messages.extend(build_model_logs)

        log_messages.append(f"Solver status: {status}")

        if status in ("OK", "OPTIMAL", "FEASIBLE") and wide_df is not None and not wide_df.empty:
            
            # wide_df는 실제로는 long-form이므로, wide-to-long 변환이 불필요.
            # 컬럼명 변경도 필요 없음.
            try:
                long_df = wide_df.copy()
                long_df['interview_date'] = the_date
                
                # 'code' 열이 없으면 'job_code'를 사용
                if 'code' not in long_df.columns and 'job_code' in long_df.columns:
                    long_df = long_df.rename(columns={'job_code': 'code'})

                # 'loc' 열이 없으면 'room'을 사용
                if 'loc' not in long_df.columns and 'room' in long_df.columns:
                    long_df = long_df.rename(columns={'room': 'loc'})
                
                # start_time, end_time -> start, end로 정규화
                if 'start_time' in long_df.columns:
                    long_df = long_df.rename(columns={'start_time': 'start'})
                if 'end_time' in long_df.columns:
                    long_df = long_df.rename(columns={'end_time': 'end'})


                scheduled_ids_today = set(long_df['id'].unique())
                all_scheduled_ids.update(scheduled_ids_today)
                
                all_scheduled_cands_long = pd.concat([all_scheduled_cands_long, long_df], ignore_index=True)
                log_messages.append(f"성공: {len(scheduled_ids_today)}명 배정 완료.")
            except Exception as e:
                log_messages.append(f"결과 처리 중 오류: {e}")

        else:
            log_messages.append("실패 또는 배정된 지원자 없음.")
            if status == "ERROR":
                log_messages.append("\n>> 오류로 인해 스케줄링에 실패했습니다. 위의 상세 로그(Traceback)를 확인해주세요. <<\n")
    
    else: # for-else: break 없이 루프가 끝나면 실행
        unscheduled_cands_final = candidates_df[~candidates_df['id'].isin(all_scheduled_ids)]
        if not unscheduled_cands_final.empty:
            log_messages.append(f"⚠️ {max_days}일 안에 {len(unscheduled_cands_final['id'].unique())}명의 지원자를 모두 배정하지 못했습니다.")
            st.warning(f"시뮬레이션 기간({max_days}일)이 초과되었습니다. 일부 지원자가 배정되지 못했습니다.")

    if all_scheduled_cands_long.empty:
        return "NO_SOLUTION", None, "\n".join(log_messages), daily_candidate_limit
    
    # 누적된 그룹 정보를 session_state에 저장
    if all_group_info['member_to_group']:
        st.session_state['last_group_info'] = all_group_info
        log_messages.append(f"총 {len(all_group_info['member_to_group'])}명의 그룹 정보 저장됨")
    else:
        st.session_state['last_group_info'] = None

    # 최종적으로 long 포맷을 wide 포맷으로 변환
    final_wide = all_scheduled_cands_long.pivot_table(
        index=['id', 'interview_date', 'code'],
        columns='activity',
        values=['start', 'end', 'loc'],
        aggfunc='first'
    ).reset_index()

    final_wide.columns = ['_'.join(col).strip() if isinstance(col, tuple) and col[1] else col[0] for col in final_wide.columns]
    final_wide = final_wide.rename(columns={'id_': 'id', 'interview_date_': 'interview_date', 'code_': 'code'})

    activity_cols = sorted(list(all_scheduled_cands_long['activity'].unique()))
    
    for act in activity_cols:
        for prefix in ['start_', 'end_']:
            col = f"{prefix}{act}"
            if col in final_wide.columns:
                final_wide[col] = pd.to_datetime(final_wide[col], errors='coerce').dt.strftime('%H:%M:%S')

    sorted_activity_cols = sort_activities_by_time(final_wide.copy(), activity_cols)

    base_cols = ['id', 'interview_date', 'code']
    ordered_cols = base_cols + [f'{prefix}{act}' for act in sorted_activity_cols for prefix in ['start_', 'end_', 'loc_']]
    
    final_ordered_cols = [c for c in ordered_cols if c in final_wide.columns]
    final_wide = final_wide[final_ordered_cols]
    
    # 더미 지원자 유지 (사용자 요청에 따라 제거하지 않음)
    # if 'id' in final_wide.columns:
    #     before_count = len(final_wide)
    #     final_wide = final_wide[~final_wide['id'].str.startswith('DUMMY_')]
    #     dummy_count = before_count - len(final_wide)
    #     if dummy_count > 0:
    #         log_messages.append(f"더미 지원자 {dummy_count}명 제거됨")

    return "OK", _drop_useless_cols(final_wide), "\n".join(log_messages), daily_candidate_limit

def _drop_useless_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    값이 하나도 없거나(전부 NaN/빈칸) 정보량이 0인 열을 제거한다.
    (loc_/start_/end_ 같은 이름이라도 전부 비어 있으면 삭제)
    """
    def useless(s: pd.Series) -> bool:
        return s.replace('', pd.NA).nunique(dropna=True) == 0
    return df.drop(columns=[c for c in df.columns if useless(df[c])])

def sort_activities_by_time(df: pd.DataFrame, activity_cols: list) -> list:
    """활동(activity) 컬럼들을 평균 시작 시간순으로 정렬"""
    avg_start_times = {}
    for act in activity_cols:
        start_col = f'start_{act}'
        if start_col in df.columns:
            # SettingWithCopyWarning을 피하기 위해 .loc 사용 및 타입 변환
            times = pd.to_datetime(df[start_col], errors='coerce').dropna()
            if not times.empty:
                avg_start_times[act] = times.mean()

    sorted_activities = sorted(avg_start_times.keys(), key=lambda k: avg_start_times[k])
    time_missing_activities = sorted([act for act in activity_cols if act not in avg_start_times])
    return sorted_activities + time_missing_activities

def solve(cfg_ui: dict, params: dict | None = None, *, debug: bool = False):
    """
    cfg_ui : core.build_config()가 넘긴 UI 데이터 묶음(dict)
    params : 스케줄링 파라미터 (dict)
    반환   : (status:str, wide:pd.DataFrame|None, logs:str)
    """
    import io, contextlib, traceback, sys
    import pandas as pd
    import streamlit as st
    from interview_opt_test_v4 import build_model

    logger = st.logger.get_logger("solver")

    # 0) 지원자 데이터 유무 체크
    if "candidates_exp" not in cfg_ui or cfg_ui["candidates_exp"].empty:
        st.error("⛔ 지원자 데이터가 없습니다. 'Candidates' 페이지에서 데이터를 업로드해주세요.")
        return "NO_DATA", None, ""

    # --- room_cap vs activity.max_cap 하드-검증 -----------------
    room_types_ui = cfg_ui["activities"]["room_type"].dropna().unique()
    room_max = {}
    for _, rp in cfg_ui["room_plan"].iterrows():
        for rt in room_types_ui:
            col = f"{rt}_cap"
            if col in rp and pd.notna(rp[col]):
                room_max[rt] = max(room_max.get(rt, 0), int(rp[col]))
    bad = [
        (row.activity, row.max_cap, room_max.get(row.room_type, 0))
        for _, row in cfg_ui["activities"].iterrows()
        if "max_cap" in row and "room_type" in row and pd.notna(row.max_cap) and pd.notna(row.room_type) and row.max_cap > room_max.get(row.room_type, 0)
    ]
    if bad:
        msg = ", ".join(f"{a}(max {mc}>{rc})" for a,mc,rc in bad)
        st.error(f"⛔ room_plan cap 부족: {msg}")
        return "ERR", None, ""
    # ----------------------------------------------------------

    # 날짜 리스트 추출: 지원자 날짜와 Room Plan 날짜의 교집합만 사용
    df_raw_all = cfg_ui["candidates_exp"].copy()
    df_raw_all["interview_date"] = pd.to_datetime(df_raw_all["interview_date"])
    candidate_dates = set(df_raw_all["interview_date"].dt.date)

    room_plan_df = cfg_ui["room_plan"].copy()
    if "date" not in room_plan_df.columns:
        st.error("⛔ 'Room Plan'에 'date' 컬럼이 없습니다. 설정을 확인해주세요.")
        return "ERR_NO_ROOM_DATE", None, ""
    room_plan_df["date"] = pd.to_datetime(room_plan_df["date"])
    room_plan_dates = set(room_plan_df["date"].dt.date)

    date_list_obj = sorted(list(candidate_dates.intersection(room_plan_dates)))

    if not date_list_obj:
        st.error(
            "**설정 오류:** 지원자가 배정된 날짜와 'Room Plan'에 설정된 날짜가 일치하지 않습니다. "
            f"지원자 날짜: `{sorted(list(candidate_dates))}`, "
            f"Room Plan 날짜: `{sorted(list(room_plan_dates))}`. "
            "두 설정의 날짜가 적어도 하루는 일치해야 스케줄링이 가능합니다."
        )
        return "NO_VALID_DATE", None, ""

    date_list = [pd.to_datetime(d) for d in date_list_obj]

    all_wide = []
    all_logs = []
    for the_date in date_list:
        # (1) 하루치 지원자만 필터
        day_df_raw = df_raw_all[df_raw_all["interview_date"] == the_date]

        # (2) 내부 표 4개 생성 (기존 로직 재활용)
        internal = _derive_internal_tables(cfg_ui, the_date, debug=debug)
        
        # ----------------------------------------------------------
        # build_model에 필요한 데이터 구조 생성
        # ----------------------------------------------------------
        activities_df = cfg_ui['activities']
        act_info = {
            row['activity']: {
                'duration': int(row['duration_min']),
                'min_ppl': int(row.get('min_cap', 1)),
                'max_ppl': int(row.get('max_cap', 1)),
                'required_rooms': [row['room_type']]
            }
            for _, row in activities_df.iterrows()
        }

        candidate_info = {
            cid: {
                'job_code': group['code'].iloc[0],
                'activities': group['activity'].tolist()
            }
            for cid, group in day_df_raw.groupby('id')
        }

        cfg_avail_day = internal['cfg_avail'][internal['cfg_avail']['date'] == the_date]
        room_info = {
            row['loc']: {'capacity': int(row['capacity_max'])}
            for _, row in cfg_avail_day.iterrows()
        }

        cfg_oper_day = internal['cfg_oper'][internal['cfg_oper']['date'] == the_date]
        oper_hours = {}
        base_time = pd.to_datetime(the_date.date().strftime('%Y-%m-%d') + ' 00:00:00')
        for _, row in cfg_oper_day.iterrows():
            start_dt = pd.to_datetime(f"{the_date.date()} {row['start_time']}")
            end_dt = pd.to_datetime(f"{the_date.date()} {row['end_time']}")
            start_minutes = int((start_dt - base_time).total_seconds() / 60)
            end_minutes = int((end_dt - base_time).total_seconds() / 60)
            oper_hours[row['code']] = (start_minutes, end_minutes)
        
        rules = [
            (row['predecessor'], row['successor'], 'direct')
            for _, row in cfg_ui['precedence'].iterrows()
        ]
        
        config = {
            **(params or {}),
            'the_date': the_date,
            'debug_mode': debug,
            'num_cpus': 8,
            'act_info': act_info,
            'candidate_info': candidate_info,
            'room_info': room_info,
            'oper_hours': oper_hours,
            'rules': rules,
            'min_gap_min': params.get('min_gap_min', 5) if params else 5,
            'time_limit_sec': 60.0
        }
        
        log_buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(log_buf):
                model, status_name, final_report_df, logs = build_model(config, logger)
                if logs:
                    all_logs.extend(logs)
                wide = final_report_df
        except Exception:
            tb_str = traceback.format_exc()
            st.error("❌ Solver exception:")
            st.code(tb_str)
            st.code(log_buf.getvalue())
            return "ERR", None, log_buf.getvalue()

        all_logs.append(log_buf.getvalue())
        if status_name not in ["OPTIMAL", "FEASIBLE"]:
            st.error(f"⚠️ Solver status: {status_name} (date {the_date.date()})")
            st.code(log_buf.getvalue())
            return status_name, None, "\n".join(all_logs)

        all_wide.append(wide)

    if not all_wide:
        st.info("ℹ️ 해당 조건으로 배치 가능한 지원자가 없습니다.")
        return "NO_FEASIBLE_DATE", None, "\n".join(all_logs)

    all_long = []
    for df_w in all_wide:
        id_vars = [c for c in df_w.columns if not (c.startswith('start_') or c.startswith('end_') or c.startswith('loc_'))]
        # end_D -> end_ 로 미리 변경
        df_w.columns = df_w.columns.str.replace("end_D", "end_")
        
        activities_in_df = set()
        for c in df_w.columns:
            if c.startswith('start_'): activities_in_df.add(c.replace('start_',''))
            elif c.startswith('end_'): activities_in_df.add(c.replace('end_',''))
            elif c.startswith('loc_'): activities_in_df.add(c.replace('loc_',''))

        if not activities_in_df:
            continue

        df_l = pd.wide_to_long(df_w,
                               stubnames=['start', 'end', 'loc'],
                               i=id_vars,
                               j='activity',
                               sep='_',
                               suffix='(' + '|'.join(activities_in_df) + ')').reset_index()
        all_long.append(df_l)

    if not all_long:
        st.info("ℹ️ 조건에 맞는 스케줄 생성에 실패했습니다.")
        return "NO_FEASIBLE_SCHEDULE", None, "\n".join(all_logs)

    final_long = pd.concat(all_long, ignore_index=True)
    
    final_wide = final_long.pivot_table(
        index=[c for c in final_long.columns if c not in ['activity', 'start', 'end', 'loc']],
        columns='activity',
        values=['start', 'end', 'loc']
    ).reset_index()

    final_wide.columns = [f'{v}_{c}' if c else v for v,c in final_wide.columns]
    
    activity_cols = sorted(list(final_long['activity'].unique()))
    # copy()를 사용하여 SettingWithCopyWarning 방지
    sorted_activity_cols = sort_activities_by_time(final_wide.copy(), activity_cols)

    base_cols = [c for c in ['id', 'interview_date', 'code'] if c in final_wide.columns]
    ordered_cols = base_cols + [f'{prefix}{act}' for act in sorted_activity_cols for prefix in ['start_', 'end_', 'loc_']]
    
    final_ordered_cols = [c for c in ordered_cols if c in final_wide.columns]
    final_wide = final_wide[final_ordered_cols]
    
    return "OK", _drop_useless_cols(final_wide), "\n".join(all_logs)
