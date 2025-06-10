# solver/solver.py  –  UI 데이터만으로 OR-Tools 실행
from datetime import timedelta
import pandas as pd
import traceback, sys, streamlit as st
from interview_opt_test_v4 import build_model   # ← 원본 거대한 함수 재사용
import contextlib, io
import yaml
from interview_opt_test_v4 import YAML_FILE
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
import pandas as pd   # <= solver/solver.py 상단 import 부분에 이미 있다면 생략

def load_param_grid(csv_path: str = "parameter_grid_test_v4.csv") -> pd.DataFrame:
    """
    parameter_grid_test_v4.csv 를 읽어서 빈칸은 '' 로 채운 DataFrame 반환.
    RunScheduler 페이지 드롭다운/실행용 공통 헬퍼.
    """
    return pd.read_csv(csv_path).fillna("")
# ──────────────────────────────────────────────
def _derive_internal_tables(cfg_ui: dict, *, debug: bool = False) -> dict:
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
        # 외부에서 loc · cap 이 이미 준비돼 있으면 그대로 활용
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
        # room_plan → loc 폭발 (room_type 동적)
        rp, rows = cfg_ui["room_plan"], []
        for _, r in rp.iterrows():
            for base in room_types_ui:
                n = int(r.get(f"{base}_count", 0))
                if n == 0:
                    continue
                for i in range(1, n + 1):
                    loc = f"{base}{chr(64+i)}" if n > 1 else base
                    rows.append({"room_type": base, "loc": loc})
        exploded = pd.DataFrame(rows).drop_duplicates("loc")
        cfg_map = (
            base_map.merge(exploded, on="room_type", how="left")
                    .drop(columns=["room_type"])
        )

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
                cap = int(r.get(f"{base}_cap", 0))
                for i in range(1, n + 1):
                    loc = f"{base}{chr(64+i)}" if n > 1 else base
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
        st.markdown("#### 🐞 `cfg_map` (activity ↔ loc) – 상위 20행")
        st.dataframe(cfg_map.sort_values(["activity", "loc"]).head(20),
                     use_container_width=True)

        first_date = cfg_avail["date"].min()
        st.markdown(f"#### 🐞 `cfg_avail` ({first_date.date()} 기준) – 상위 20행")
        st.dataframe(cfg_avail.loc[cfg_avail["date"] == first_date]
                               .sort_values("loc").head(20),
                     use_container_width=True)
        st.markdown("---")

    # 결과 반환 --------------------------------------
    return dict(
        cfg_duration=cfg_duration,
        cfg_map=cfg_map,
        cfg_avail=cfg_avail,
        cfg_oper=cfg_oper,
        group_meta=cfg_ui["activities"].copy(),   # 추가 필드
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
# ──────────────────────────────────────────────
# 3) 최상위 호출 함수 – Streamlit에서 여기만 사용
#    ★ 여러 날짜(6/4‥6/7 등)를 모두 처리하도록 수정 버전 ★
# ──────────────────────────────────────────────
def solve(cfg_ui: dict, params: dict | None = None, *, debug: bool = False):
    """
    cfg_ui : core.build_config()가 넘긴 UI 데이터 묶음(dict)
    params : wave_len·max_wave … 등 시나리오 한 줄(dict)
    반환   : (status:str, wide:pd.DataFrame|None)
    """
    import io, contextlib, traceback, sys
    import pandas as pd
    import streamlit as st
    from interview_opt_test_v4 import build_model

    # 0) 지원자 데이터 유무 체크
    if cfg_ui["candidates_exp"].empty:
        st.error("⛔ 지원자 데이터가 없습니다.")
        return "NO_DATA", None

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
        if row.max_cap > room_max.get(row.room_type, 0)
    ]
    if bad:
        msg = ", ".join(f"{a}(max {mc}>{rc})" for a,mc,rc in bad)
        st.error(f"⛔ room_plan cap 부족: {msg}")
        return "ERR", None
    # ----------------------------------------------------------

    # 날짜 리스트 추출 (여러 날짜 한꺼번에)
    df_raw_all = cfg_ui["candidates_exp"].copy()
    df_raw_all["interview_date"] = pd.to_datetime(df_raw_all["interview_date"])
    date_list = sorted(df_raw_all["interview_date"].unique())

    all_wide = []
    for the_date in date_list:
        # (1) 하루치 지원자만 필터
        day_df_raw = df_raw_all[df_raw_all["interview_date"] == the_date]

        # (2) 내부 표 4개 생성 & df_raw 주입
        internal = _derive_internal_tables(cfg_ui, debug=debug)
        internal["df_raw"] = day_df_raw
        
        # (3) precedence 룰을 YAML 형식으로 (토큰 룰을 확장한 뒤)
        prec_yaml_ui = df_to_yaml_dict(cfg_ui["precedence"])

        # (5) build_model 호출용 merged dict 구성
        merged = {**internal, **cfg_ui}
        merged["prec_yaml"] = prec_yaml_ui

        # 캡처 준비
        f = io.StringIO()

        # ── (디버그) build_model 직전 테이블 확인
        if debug:
            st.markdown("##### 🐞 build_model 호출 직전 스냅샷")
            st.dataframe(internal["cfg_map"].head(20), use_container_width=True)
            st.dataframe(
                internal["cfg_avail"].query("date == @the_date").head(20),
                use_container_width=True
            )
            st.dataframe(day_df_raw.head(30), use_container_width=True)
            st.markdown("---")

        # (6) 실제 OR-Tools 모델 실행
        try:
            with contextlib.redirect_stdout(f):
                status, wide = build_model(the_date, params or {}, merged)
        except Exception:
            tb_str = traceback.format_exc()
            st.error("❌ Solver exception:")
            st.code(tb_str)
            st.code(f.getvalue())
            return "ERR", None

        # (7) 하루치 실패 → 전체 실패
        if status != "OK":
            st.error(f"⚠️ Solver status: {status} (date {the_date.date()})")
            st.code(f.getvalue())
            return status, None

        all_wide.append(wide)

    # ── 모든 날짜 성공 시: 하나로 합쳐 반환
    full_wide = pd.concat(all_wide, ignore_index=True)
    full_wide = _drop_useless_cols(full_wide)

    if debug:
        print("[solver.solve] dates:", date_list, file=sys.stderr)

    return "OK", full_wide
