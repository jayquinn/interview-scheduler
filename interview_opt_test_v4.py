# %%
# ──────────────────────────────────────
import itertools, pandas as pd        # ← import 는 그대로

def _build_param_grid() -> pd.DataFrame:       # ★ 새 함수
    seed_rows = [
        dict(priority=0, scenario_id="S_SAFE", wave_len=35, max_wave=18,
             br_offset_A=4, br_offset_B=3, min_gap_min=5, tl_sec=30)
    ]

    grid = []
    for wl, mw, brA, brB, mg in itertools.product(
            [35], [18], [-2,-1,0,1,2], [-2,-1,0,1,2], [5]):
        if wl==50 and mw==16 and brA==3 and brB==2 and mg==5:
            continue
        pr = 1
        if wl > 35: pr += 1
        if mw < 14: pr += 1
        if mg > 10: pr += 1
        grid.append(dict(priority=pr, wave_len=wl, max_wave=mw,
                         br_offset_A=brA, br_offset_B=brB,
                         min_gap_min=mg, tl_sec=30))

    df = (pd.DataFrame(seed_rows + grid)
            .sort_values(["priority","wave_len","min_gap_min","max_wave"])
            .reset_index(drop=True))

    if "scenario_id" not in df.columns:
        df.insert(0, "scenario_id",
                  [f"S{str(i+1).zfill(3)}" for i in range(len(df))])
    else:
        mask = df["scenario_id"].isna() | (df["scenario_id"]=="")
        df.loc[mask, "scenario_id"] = [
            f"S{str(i+1).zfill(3)}" for i in range(mask.sum())
        ]
    return df
# ──────────────────────────────────────


# %%
# interview_opt_test_v4.py
# -*- coding: utf-8 -*-
"""
============================================================
Interview Schedule Optimiser – multi-date / multi-grid
============================================================
* parameter_grid_test_v4.csv 에 정의된 파라미터 세트 × 날짜를 순차 탐색
* 첫 SAT+하드룰 통과 해를 찾으면 그 날짜는 종료
* 결과는 schedule_wide.csv 로 누적 저장, 시도 내역은 run_log.csv 기록
"""
# ────────────────────────────────
# 0. 공통 import & 상수
# ────────────────────────────────
import sys, itertools, time
from datetime import timedelta
from pathlib import Path
from collections import defaultdict
import yaml
import pandas as pd, yaml
from pandas.api.types import is_integer_dtype
from ortools.sat.python import cp_model
from tqdm import tqdm
import traceback

# 고정 파일 경로
CAND_CSV = Path("candidate_activities_input_before_test_v4_HF.csv")
GRID_CSV = Path("parameter_grid_test_v4.csv")
YAML_FILE = Path("precedence_config_test_v4_HF.yaml")

OUT_WIDE = Path("schedule_wide_test_v4_HF.csv")
OUT_LOG  = Path("log/run_log_test_v4_HF.csv")
Path("log").mkdir(exist_ok=True)          # log 폴더 보장
from types import SimpleNamespace

def load_params(row):
    """grid CSV 한 행 → 네임스페이스 객체"""
    return SimpleNamespace(
        wave_len     = int(row.wave_len),
        max_wave     = int(row.max_wave),
        br_offset_A  = int(row.br_offset_A),
        br_offset_B  = int(row.br_offset_B),
        min_gap_min  = int(row.min_gap_min),
        tl_sec       = int(row.tl_sec),
    )
# ── activities helper ─────────────────────────────────────
def get_all_activities(yaml_path: Path, df_candidates: pd.DataFrame) -> list[str]:
    """precedence YAML + CSV에서 활동명 set 추출 → 알파벳순 list"""
    prec = yaml.safe_load(open(yaml_path, encoding="utf-8"))

    acts = set(df_candidates["activity"].unique())          # ① CSV에 실제 등장
    # ② YAML – common
    for r in prec.get("common", []):
        acts.update([r["predecessor"], r["successor"]])
    # ③ YAML – by_code
    for branches in prec.get("by_code", {}).values():
        for rules in branches.values():
            for r in rules:
                acts.update([r["predecessor"], r["successor"]])
    return sorted(acts)
# ───────────────────────────────────────────────────────────

# ─────────── 사이클 검증 함수 정의 ───────────
def detect_cycle(edges):
    """
    edges: [(pred, succ), …] 리스트.
    순환이 있으면 True 반환.
    """
    # 1) 그래프 생성
    g = defaultdict(list)
    nodes = set()
    for u, v in edges:
        g[u].append(v)
        nodes.add(u)
        nodes.add(v)

    visited, onstack = set(), set()
    def dfs(u):
        visited.add(u)
        onstack.add(u)
        for w in g.get(u, []):
            if w not in visited:
                if dfs(w):
                    return True
            elif w in onstack:
                return True
        onstack.remove(u)
        return False

    # 2) 미리 추출한 노드 집합으로 순환 검사
    return any(dfs(node) for node in nodes if node not in visited)
# ───────────────────────────────────────────────
def expand_availability(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    UI 에서 받은 집계형 space_availability
      (date · *_count · *_cap · 사용여부 …)
    → solver 가 요구하는
      (date · loc · capacity_max/override) 행 단위 DF 로 변환
    """
    rows = []
    ROOM_TYPES = [
        ("발표면접실", "발표면접실_cap",   "발표면접실_count"),
        ("심층면접실", "심층면접실_cap",   "심층면접실_count"),
        ("커피챗실",   "커피챗실_cap",     "커피챗실_count"),
        ("발표준비실", "발표준비실_cap",   "발표준비실_count"),
        ("인인검사실", "인인검사실_cap",   "인인검사실_count"),   # ← 추가
        ("토토면접실", "토토면접실_cap",   "토토면접실_count"),   # ← 추가
    ]

    for _, r in df_raw.iterrows():
        if str(r.get("사용여부", "TRUE")).upper() == "FALSE":
            continue                      # 사용 안 하는 날짜면 skip
        date = pd.to_datetime(r["date"])
        for base, cap_col, cnt_col in ROOM_TYPES:
            n_room = int(r[cnt_col])
            cap    = int(r[cap_col])
            for i in range(1, n_room + 1):
                loc = f"{base}{chr(64+i)}"        # A,B,C…
                rows.append({
                    "date":           date,
                    "loc":            loc,
                    "capacity_max":   cap,        # capacity_override 로 쓰셔도 OK
                })
    return pd.DataFrame(rows)

# ────────────────────────────────
# 1. 하드-룰 검증 함수 (순서 + Wave 정렬)
# ────────────────────────────────
# --- 간결해진 verify_rules ---
# ─── PATCH-3 : 기존 verify_rules() 함수 통째로 갈아끼우기 ───
def verify_rules(wide_df: pd.DataFrame, rules: list) -> list:
    """
    wide_df에 선후행 규칙이 지켜졌는지 검증합니다.
    """
    err_msgs = []
    if wide_df.empty:
        return err_msgs

    for _, row in wide_df.iterrows():
        times = {}
        for col in row.index:
            if col.startswith(('start_', 'end_')) and pd.notna(row[col]):
                parts = col.split('_', 1)
                times[(parts[0], parts[1])] = row[col]

        for pred, succ, _ in rules:
            if pred == '__START__':
                succ_start_time = times.get(('start', succ))
                if succ_start_time is None: continue
                
                is_earliest = True
                for (typ, act), time in times.items():
                    if typ == 'start' and act != succ and time < succ_start_time:
                        is_earliest = False
                        break
                if not is_earliest:
                    err_msgs.append(f"Rule Violation: {row['id']} - {succ} is not the first activity.")

            elif succ == '__END__':
                pred_end_time = times.get(('end', pred))
                if pred_end_time is None: continue

                is_latest = True
                for (typ, act), time in times.items():
                    if typ == 'end' and act != pred and time > pred_end_time:
                        is_latest = False
                        break
                if not is_latest:
                    err_msgs.append(f"Rule Violation: {row['id']} - {pred} is not the last activity.")

            else:
                pred_end_time = times.get(('end', pred))
                succ_start_time = times.get(('start', succ))
                if pred_end_time is not None and succ_start_time is not None:
                    if pred_end_time > succ_start_time:
                        err_msgs.append(f"Rule Violation: {row['id']} - {pred} ends after {succ} starts.")
    return err_msgs


def prepare_schedule(solver, intervals, presences, room_assignments, CANDIDATE_SPACE, ACT_SPACE, ROOM_SPACE, the_date, logger):
    """
    Solver 결과를 바탕으로 wide-format DataFrame을 생성합니다.
    """
    rows = []
    base_time = pd.to_datetime(the_date.date().strftime('%Y-%m-%d') + ' 00:00:00')

    for (cid, act_name), iv in intervals.items():
        if solver.Value(presences.get((cid, act_name), 0)) == 1:
            start_min = solver.Value(iv.StartExpr())
            end_min = solver.Value(iv.EndExpr())

            start_time = base_time + pd.Timedelta(minutes=start_min)
            end_time = base_time + pd.Timedelta(minutes=end_min)
            
            assigned_room = "N/A"
            if room_assignments:
                for (r_cid, r_act, r_room), pres_var in room_assignments.items():
                    if r_cid == cid and r_act == act_name and solver.Value(pres_var) == 1:
                        assigned_room = r_room
                        break

            rows.append({
                'id': cid,
                'code': CANDIDATE_SPACE[cid]['job_code'],
                'interview_date': the_date,
                'activity': act_name,
                'loc': assigned_room,
                'start': start_time,
                'end': end_time
            })

    if not rows:
        return pd.DataFrame(), {}
        
    long_df = pd.DataFrame(rows)
    if long_df.empty:
        return pd.DataFrame(), {}

    long_df['start'] = pd.to_datetime(long_df['start'])
    long_df['end'] = pd.to_datetime(long_df['end'])

    wide_df = long_df.pivot_table(
        index=['id', 'code', 'interview_date'],
        columns='activity',
        values=['loc', 'start', 'end'],
        aggfunc='first'
    )
    
    wide_df.columns = [f'{val}_{act}' for val, act in wide_df.columns]
    wide_df = wide_df.reset_index()
    
    return wide_df, {}


# ────────────────────────────────
# 2. build_model() –  **엔진**
# ────────────────────────────────
def build_model(config, logger):
    """
    주어진 설정을 바탕으로 CP-MODEL을 빌드합니다.
    """
    model = cp_model.CpModel()
    all_logs = []

    try:
        the_date = config['the_date']
        MIN_GAP = config['min_gap_min']
        ACT_SPACE = config['act_info']
        rules = config.get('rules', [])
        CANDIDATE_SPACE = config['candidate_info']
        ROOM_SPACE = config['room_info']
        OPER_HOURS = config['oper_hours']
        CANDIDATE_ACTS = {cid: data['activities'] for cid, data in CANDIDATE_SPACE.items()}
        CIDS = list(CANDIDATE_SPACE.keys())
        
        all_rule_activities = set()
        for pred, succ, _ in rules:
            if pred != '__START__': all_rule_activities.add(pred)
            if succ != '__END__': all_rule_activities.add(succ)

        missing_activities = all_rule_activities - set(ACT_SPACE.keys())
        if missing_activities:
            raise ValueError(f"설정 오류: 다음 활동에 대한 장소(Room) 설정이 누락되었습니다: {', '.join(missing_activities)}")

        horizon = 0
        if OPER_HOURS:
            for _, (start, end) in OPER_HOURS.items():
                horizon = max(horizon, end)
        
        intervals, presences, room_assignments = {}, {}, {}

        for cid in CIDS:
            for act_name in CANDIDATE_ACTS.get(cid, []):
                if act_name in ACT_SPACE:
                    duration = ACT_SPACE[act_name]['duration']
                    suffix = f"{cid}_{act_name}"
                    start_var = model.NewIntVar(0, horizon, f'start_{suffix}')
                    end_var = model.NewIntVar(0, horizon, f'end_{suffix}')
                    presence_var = model.NewBoolVar(f'presence_{suffix}')
                    interval_var = model.NewOptionalIntervalVar(start_var, duration, end_var, presence_var, f'interval_{suffix}')
                    intervals[(cid, act_name)] = interval_var
                    presences[(cid, act_name)] = presence_var
                    model.Add(presence_var == 1)

        for cid in CIDS:
            cid_intervals = [iv for (c, _), iv in intervals.items() if c == cid]
            if len(cid_intervals) > 1:
                model.AddNoOverlap(cid_intervals)

        if MIN_GAP > 0:
            for cid in CIDS:
                acts = CANDIDATE_ACTS.get(cid, [])
                for i in range(len(acts)):
                    for j in range(i + 1, len(acts)):
                        act1, act2 = acts[i], acts[j]
                        if (cid, act1) in intervals and (cid, act2) in intervals:
                            iv1, iv2 = intervals[(cid, act1)], intervals[(cid, act2)]
                            b = model.NewBoolVar(f'gap_{cid}_{act1}_{act2}')
                            model.Add(iv2.StartExpr() >= iv1.EndExpr() + MIN_GAP).OnlyEnforceIf(b)
                            model.Add(iv1.StartExpr() >= iv2.EndExpr() + MIN_GAP).OnlyEnforceIf(b.Not())

        room_intervals = defaultdict(list)
        for (cid, act_name), iv in intervals.items():
            required_rooms = ACT_SPACE[act_name].get('required_rooms', [])
            possible_rooms = [r_name for r_type in required_rooms for r_name in ROOM_SPACE if r_name.startswith(r_type)]
            
            room_presence_vars = []
            for room_name in possible_rooms:
                presence_var = model.NewBoolVar(f'presence_{cid}_{act_name}_{room_name}')
                room_assignments[(cid, act_name, room_name)] = presence_var
                room_presence_vars.append(presence_var)
                
                v_iv = model.NewOptionalIntervalVar(iv.StartExpr(), ACT_SPACE[act_name]['duration'], iv.EndExpr(), presence_var, f'v_iv_{cid}_{act_name}_{room_name}')
                room_intervals[room_name].append(v_iv)
            
            if room_presence_vars:
                model.AddExactlyOne(room_presence_vars)

        for room_name, iv_list in room_intervals.items():
            if len(iv_list) > 1:
                capacity = ROOM_SPACE[room_name].get('capacity', 1)
                model.AddCumulative(iv_list, [1]*len(iv_list), capacity)

        for pred, succ, _ in rules:
            for cid in CIDS:
                acts = CANDIDATE_ACTS.get(cid, [])
                if pred == '__START__' and succ in acts and (cid, succ) in intervals:
                    succ_iv = intervals[(cid, succ)]
                    for act_name in acts:
                        if act_name != succ and (cid, act_name) in intervals:
                            model.Add(intervals[(cid, act_name)].StartExpr() >= succ_iv.EndExpr())
                elif succ == '__END__' and pred in acts and (cid, pred) in intervals:
                    pred_iv = intervals[(cid, pred)]
                    for act_name in acts:
                        if act_name != pred and (cid, act_name) in intervals:
                            model.Add(intervals[(cid, act_name)].EndExpr() <= pred_iv.StartExpr())
                elif pred in acts and succ in acts and (cid, pred) in intervals and (cid, succ) in intervals:
                    model.Add(intervals[(cid, succ)].StartExpr() >= intervals[(cid, pred)].EndExpr())

        for cid, data in CANDIDATE_SPACE.items():
            if data['job_code'] in OPER_HOURS:
                start_time, end_time = OPER_HOURS[data['job_code']]
                for act_name in CANDIDATE_ACTS.get(cid, []):
                    if (cid, act_name) in intervals:
                        iv = intervals[(cid, act_name)]
                        model.Add(iv.StartExpr() >= start_time)
                        model.Add(iv.EndExpr() <= end_time)

        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = config.get('num_cpus', 8)
        solver.parameters.log_search_progress = True
        status = solver.Solve(model)
        status_name = solver.StatusName(status)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            final_report_df, _ = prepare_schedule(solver, intervals, presences, room_assignments, CANDIDATE_SPACE, ACT_SPACE, ROOM_SPACE, the_date, logger)
            err_msgs = verify_rules(final_report_df, rules)
            if err_msgs:
                logger.warning("Rule violations found:")
                for msg in err_msgs: logger.warning(msg)
                status_name = 'RULE_VIOLATED'
        else:
            final_report_df = pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error during model building or solving: {e}", exc_info=True)
        status_name = "ERROR"
        final_report_df = pd.DataFrame()
        all_logs.append(f"\n--- EXCEPTION TRACEBACK ---\n{traceback.format_exc()}")

    return model, status_name, final_report_df, all_logs


# ────────────────────────────────
# 3. main –  날짜 × 파라미터 루프
# ────────────────────────────────
def main():
    # ── 0) 지원자 CSV 한 번만 읽기 ──────────────────────────────
    df_raw = (
        pd.read_csv(CAND_CSV, encoding="utf-8-sig")      # 필요하면 utf-8-sig, cp949
          .assign(activity=lambda d: d["activity"].str.split(","))
          .explode("activity")
          .assign(activity=lambda d: d["activity"].str.strip())
          .assign(
              interview_date=lambda d:
                  pd.to_datetime(d["interview_date"], errors="coerce")
          )
    )

    # ── 1) 날짜 리스트 자동 생성 ────────────────────────────────
    date_list = (
        pd.to_datetime(df_raw["interview_date"].dropna().unique())
    )
    date_list = pd.DatetimeIndex(date_list).sort_values()

    # ── 2) 공통 cfg 모음 ───────────────────────────────────────
    cfg = {
        "df_raw"       : df_raw,                              # ← 재활용
        "cfg_duration" : pd.read_csv("duration_config_test_v4_HF.csv"),
        "cfg_avail"    : pd.read_csv("space_availability_test_v4_HF.csv",
                                     parse_dates=["date"]),
        "cfg_map"      : pd.read_csv("activity_space_map_test_v4_HF.csv"),
        "cfg_oper"     : pd.read_csv("operating_config_test_v4_HF.csv",
                                     parse_dates=["date"]),
    }

    # (3) 파라미터 그리드
    grid = pd.read_csv(GRID_CSV, dtype=str).fillna('')
    if 'scenario_id' not in grid.columns:
        grid.insert(0, 'scenario_id', range(1, len(grid)+1))
    if 'tl_sec' not in grid.columns:
        grid['tl_sec'] = '30'
    for col, default in [("br_offset_A", "2"), ("br_offset_B", "1")]:
        if col not in grid.columns:
            grid[col] = default

    # (4) 실행
    all_wides, log_rows = [], []
    for d in tqdm(date_list, desc="Dates"):

        ok_found = False
        for _, p in grid.iterrows():
            params = {k: (int(v) if str(v).lstrip('-').isdigit() else v) for k,v in p.items()}
            status, wide = build_model(d, params, cfg)
            if status == "NO_DATA":
                continue      # 해당 날짜에 지원자 없음
            log_rows.append({
                "date"    : d.date(),
                "scenario": p["scenario_id"],
                "status"  : status,
                "success" : 1 if status == "OK" else 0
            })


            if status == "OK":
                all_wides.append(wide)
                ok_found = True
                break   # 다음 날짜

        if not ok_found:
            print(f"[WARN] {d.date()} – feasible 해 없음")

    # (5) 저장
    pd.DataFrame(log_rows).to_csv(OUT_LOG, mode='w', index=False,
                              encoding="utf-8-sig")

    if all_wides:
        pd.concat(all_wides).to_csv(OUT_WIDE, index=False, encoding="utf-8-sig")
        print(f"[SAVE] {OUT_WIDE}")
    print("[SAVE] run_log_test_v4.csv")


# ────────────────────────────────
# 4. 실행
# ────────────────────────────────
if __name__ == "__main__":
    # (1) 파라미터 그리드 csv 저장 – 스크립트를 직접 실행할 때만
    _build_param_grid().to_csv(
        "parameter_grid_test_v4.csv",
        index=False, encoding="utf-8-sig")
    print("📝 parameter_grid_test_v4.csv 생성 완료")

    # (2) 기존 main() 호출
    main()
