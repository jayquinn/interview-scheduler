# solver/solver.py  –  UI 데이터만으로 OR-Tools 실행
from datetime import timedelta, datetime, date
import pandas as pd
import traceback, sys, streamlit as st
from interview_opt_test_v4 import build_model   # ← 원본 거대한 함수 재사용
import contextlib, io
import yaml
import itertools
from pathlib import Path

def df_to_yaml_dict(df: pd.DataFrame) -> dict:
    rules = []
    for r in df.itertuples(index=False):
        rule = {
            "predecessor": r.predecessor,
            "successor": r.successor,
            "min_gap_min": int(r.gap_min),
            "adjacent": bool(getattr(r, "adjacent", False))
        }
        rules.append(rule)
    return {"common": rules, "by_code": {}}








# ────────────────────────────────────────────────────────
# 0. 시나리오(파라미터) 그리드 로더  ★ RunScheduler 페이지에서 사용
# ────────────────────────────────────────────────────────
def _build_param_grid() -> pd.DataFrame:
    """기본 파라미터 그리드를 생성합니다."""
    seed_rows = [
        dict(priority=0, scenario_id="S_SAFE", wave_len=35, max_wave=18,
             br_offset_A=4, br_offset_B=3, min_gap_min=5, tl_sec=30)
    ]
    grid = []
    for wl, mw, brA, brB, mg in itertools.product(
            [35], [18], [-2, -1, 0, 1, 2], [-2, -1, 0, 1, 2], [5]):
        if wl == 50 and mw == 16 and brA == 3 and brB == 2 and mg == 5:
            continue
        pr = 1
        if wl > 35: pr += 1
        if mw < 14: pr += 1
        if mg > 10: pr += 1
        grid.append(dict(priority=pr, wave_len=wl, max_wave=mw,
                         br_offset_A=brA, br_offset_B=brB,
                         min_gap_min=mg, tl_sec=30))
    df = (pd.DataFrame(seed_rows + grid)
            .sort_values(["priority", "wave_len", "min_gap_min", "max_wave"])
            .reset_index(drop=True))
    if "scenario_id" not in df.columns:
        df.insert(0, "scenario_id", [f"S{str(i+1).zfill(3)}" for i in range(len(df))])
    else:
        mask = df["scenario_id"].isna() | (df["scenario_id"] == "")
        df.loc[mask, "scenario_id"] = [f"S{str(i+1).zfill(3)}" for i in range(mask.sum())]
    return df

def load_param_grid(csv_path: str = "parameter_grid_test_v4.csv") -> pd.DataFrame:
    """
    parameter_grid_test_v4.csv를 읽어서 반환합니다.
    파일이 없으면 기본값으로 생성합니다.
    """
    if not Path(csv_path).exists():
        df = _build_param_grid()
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return pd.read_csv(csv_path).fillna("")

# ──────────────────────────────────────────────
def _derive_internal_tables(cfg_ui: dict, the_date: pd.Timestamp, *, debug: bool = False) -> dict:
    """
    Streamlit UI 값으로부터 build_model 이 바로 쓸 4개 표를 생성.
    debug=True 이면 브라우저에 cfg_map / cfg_avail 미리보기 출력.
    """

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
                    loc = f"{base}{i}" if n > 1 else base
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
                    loc = f"{base}{i}" if n > 1 else base
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

# ──────────────────────────────────────────────
# ★ 빈 칼럼 자동 삭제용 헬퍼 ★
# ──────────────────────────────────────────────
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

# ──────────────────────────────────────────────
# 3) 최상위 호출 함수 – Streamlit에서 여기만 사용
#    ★ 여러 날짜(6/4‥6/7 등)를 모두 처리하도록 수정 버전 ★
# ──────────────────────────────────────────────
def solve(cfg_ui: dict, params: dict | None = None, *, debug: bool = False):
    """
    cfg_ui : core.build_config()가 넘긴 UI 데이터 묶음(dict)
    params : wave_len·max_wave … 등 시나리오 한 줄(dict)
    반환   : (status:str, wide:pd.DataFrame|None, logs:str)
    """

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
    job_acts_map: pd.DataFrame
) -> int:
    """사용 가능한 자원(시간, 공간)과 지원자별 필요 자원을 기반으로 일일 처리 가능 인원을 동적으로 추정합니다."""
    
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
    
    return max(10, daily_capacity)

def solve_for_days(cfg_ui: dict, params: dict, debug: bool):
    """
    최소 운영일을 추정하기 위한 메인 솔버 함수.
    Day 1부터 시작하여 모든 지원자가 배정될 때까지 날짜를 늘려가며 시도.
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
            job_acts_map=job_acts_map
        )
    except Exception as e:
        logger.warning(f"동적 일일 처리량 계산 실패: {e}. 기본값(70)으로 대체합니다.")
        daily_candidate_limit = 70
    # ++++++++++++++++++++++++++++++

    # 3. 날짜를 늘려가며 스케줄링 시도
    all_scheduled_cands_long = pd.DataFrame()
    log_messages = []
    
    max_days = 30
    all_scheduled_ids = set()
    
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
            for i in range(1, count + 1):
                loc = f"{rt}{i}" if count > 1 else rt
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

        model, status, wide_df, build_model_logs = build_model(config, logger)
        
        if build_model_logs:
            log_messages.extend(build_model_logs)

        log_messages.append(f"Solver status: {status}")

        if status in ("OPTIMAL", "FEASIBLE") and wide_df is not None and not wide_df.empty:
            
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

    return "OK", _drop_useless_cols(final_wide), "\n".join(log_messages), daily_candidate_limit
