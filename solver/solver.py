# solver/solver.py  –  UI 데이터만으로 OR-Tools 실행
from datetime import timedelta
import pandas as pd
import traceback, sys, streamlit as st
from interview_opt_test_v4 import build_model   # ← 원본 거대한 함수 재사용
import contextlib, io
print("⚙️ room_plan snapshot:", st.session_state.get("room_plan").head())
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
def _derive_internal_tables(cfg_ui: dict) -> dict:
    """Streamlit UI 값으로부터 build_model이 바로 쓸 4개 표를 생성"""

    # ① 활동 ↔ 소요시간 ----------------------------
    cfg_duration = cfg_ui["activities"][["activity", "duration_min"]].copy()

    # ------------------------------------------------
    # ② 활동 ↔ loc(room_type)  ―― A/B… 폭발 포함
    # ------------------------------------------------
    base_map = cfg_ui["activities"][["activity", "room_type"]]

    # 먼저 space_avail 이 있으면 ― 가장 깔끔
    if "space_avail" in cfg_ui and not cfg_ui["space_avail"].empty:
        sa = cfg_ui["space_avail"]
        rows = []
        for _, row in base_map.iterrows():
            act, base = row["activity"], row["room_type"]
            for loc in sa["loc"].unique():
                if str(loc).startswith(base):
                    rows.append({"activity": act, "loc": loc})
        cfg_map = pd.DataFrame(rows)
    else:
        # space_avail 이 없으면 room_plan을 보고 직접 폭발
        rp = cfg_ui["room_plan"]
        rows = []
        for _, r in rp.iterrows():
            for base in ("발표면접실","심층면접실","커피챗실","면접준비실"):
                n = int(r.get(f"{base}_count", 1))
                for i in range(1, n+1):
                    loc = f"{base}{chr(64+i)}" if n > 1 else base
                    rows.append({"room_type": base, "loc": loc})
        # 중복 제거 후 activity 와 조인
        exploded = pd.DataFrame(rows).drop_duplicates("loc")
        cfg_map = (
            base_map.merge(exploded, on="room_type", how="left")
                    .drop(columns=["room_type"])
        )

    # ------------------------------------------------
    # ③ 날짜·방별 capacity_max  ―― A/B… 폭발 포함
    # ------------------------------------------------
    if "space_avail" in cfg_ui and not cfg_ui["space_avail"].empty:
        cfg_avail = cfg_ui["space_avail"][["loc","date","capacity_max"]].copy()
        cfg_avail["capacity_override"] = pd.NA
    else:
        rp = cfg_ui["room_plan"]
        rows = []
        for _, r in rp.iterrows():
            date = pd.to_datetime(r["date"])
            for base in ("발표면접실","심층면접실","커피챗실","면접준비실"):
                n   = int(r.get(f"{base}_count", 1))
                cap = int(r[f"{base}_cap"])
                for i in range(1, n+1):
                    loc = f"{base}{chr(64+i)}" if n > 1 else base
                    rows.append({
                        "loc": loc,
                        "date": date,
                        "capacity_max": cap,
                        "capacity_override": pd.NA,
                    })
        cfg_avail = pd.DataFrame(rows)

    # ------------------------------------------------
    # ④ 전형(code) × 날짜별 운영시간
    # ------------------------------------------------
    raw_oper = cfg_ui["oper_window"].copy()
    for col_pair in [("start", "start_time"), ("end", "end_time")]:
        orig, new = col_pair
        if new in raw_oper.columns and orig in raw_oper.columns:
            raw_oper = raw_oper.drop(columns=[orig])
    cfg_oper = (
        raw_oper.dropna(subset=["code","date",
                                "start" if "start" in raw_oper.columns else "start_time",
                                "end"   if "end"   in raw_oper.columns else "end_time"])
                .query("code != ''")
                .drop_duplicates(subset=["code","date"], keep="first")
                .reset_index(drop=True)
                .rename(columns={"start":"start_time","end":"end_time"})
    )
    cfg_oper["date"]       = pd.to_datetime(cfg_oper["date"])
    cfg_oper["start_time"] = cfg_oper["start_time"].astype(str)
    cfg_oper["end_time"]   = cfg_oper["end_time"].astype(str)

    # ------------------------------------------------
    return dict(cfg_duration=cfg_duration,
                cfg_map=cfg_map,
                cfg_avail=cfg_avail,
                cfg_oper=cfg_oper)

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
    # 0) 지원자 데이터 유무 체크
    if cfg_ui["candidates_exp"].empty:
        st.error("⛔ 지원자 데이터가 없습니다.")
        return "NO_DATA", None

    # ── 날짜 리스트 추출 (여러 날짜 한꺼번에) ──────────────────
    df_raw_all = cfg_ui["candidates_exp"].copy()
    df_raw_all["interview_date"] = pd.to_datetime(df_raw_all["interview_date"])
    date_list = sorted(pd.to_datetime(df_raw_all["interview_date"].unique()))

    all_wide = []                      # 날짜별 결과 누적
    for the_date in date_list:
        # (1) 하루치 지원자만 필터
        day_df_raw = df_raw_all[df_raw_all["interview_date"] == the_date]

        # (2) 내부 표 4개 생성 & df_raw 주입
        internal = _derive_internal_tables(cfg_ui)
        internal["df_raw"] = day_df_raw
        # ── (2½) 디버그: 모델에 넘길 테이블 미리 확인 ─────────────────
        if debug:
            st.markdown("##### 🐞 build_model 호출 직전 스냅샷")
            st.dataframe(internal["cfg_map"].head(20),      use_container_width=True)
            st.dataframe(
                internal["cfg_avail"].query("date == @the_date").head(20),
                use_container_width=True
            )
            st.dataframe(day_df_raw.head(30),              use_container_width=True)
            st.markdown("---")
        merged = {**internal, **cfg_ui}

        # (3) build_model 실행
        log_buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(log_buf):
                status, wide = build_model(the_date, params or {}, merged)
        except Exception:
            tb_str = traceback.format_exc()
            st.error("❌ Solver exception:")
            st.code(tb_str)
            st.code(log_buf.getvalue())
            return "ERR", tb_str        # 즉시 종료

        # 하루치 실패 → 전체 실패로 간주
        if status != "OK":
            st.error(f"⚠️ Solver status: {status} (date {the_date.date()})")
            st.code(log_buf.getvalue())
            return status, None

        all_wide.append(wide)

    # ── 모든 날짜 성공 시: 하나로 합쳐 반환 ───────────────────
    full_wide = pd.concat(all_wide, ignore_index=True)
    full_wide = _drop_useless_cols(full_wide)      # ← 빈 칼럼 정리 한 줄

    if debug:
        print("[solver.solve] dates:", list(date_list), file=sys.stderr)

    return "OK", full_wide
