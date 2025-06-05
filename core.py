# core.py
from io import BytesIO
from datetime import datetime, timedelta
import pandas as pd
from openpyxl import Workbook
# OR-Tools 래퍼 ───────────────────────────────────────────
from solver.solver import solve, load_param_grid   # solve()만 쓰면 충분
from interview_opt_test_v4 import prepare_schedule
from io import BytesIO
import pandas as pd
import interview_opt_test_v4 as iv4   # prepare_schedule, df_to_excel 모두 여기 들어있음
# core.py  ────────────────────────────────────────
def should_use_wave(df: pd.DataFrame) -> bool:
    """
    ‘wave 팔레트’를 쓸지 판단한다.

    * wave 컬럼이 없으면   → False
    * 값이 전부 NaN/음수   → False
    * 값이 단 하나(예: 모두 0) → False
    * 그 외(두 개 이상)    → True
    """
    if 'wave' not in df.columns:
        return False
    waves = pd.to_numeric(df['wave'], errors='coerce')   # NaN·문자 제거
    waves = waves[waves >= 0]                           # 유효 wave
    return waves.nunique() > 1                          # **두 개 이상?**

# ────────────────────────────────────────────────────────
# 1) Streamlit 세션 → Solver cfg 딕셔너리
# ────────────────────────────────────────────────────────
def build_config(state: dict) -> dict:
    """페이지 곳곳에 흩어진 DataFrame을 하나의 dict(cgf)로 묶는다."""
    empty = lambda: pd.DataFrame()                 # 빈 DF 생성 헬퍼

    cfg = {
        "activities"     : state.get("activities",     empty()),
        "job_acts_map"   : state.get("job_acts_map",   empty()),  # ← NEW
        "room_plan"      : state.get("room_plan",      empty()),
        "oper_window"    : state.get("oper_window",    empty()),
        "precedence"     : state.get("precedence",     empty()),
        "candidates"     : state.get("candidates",     empty()),
        "candidates_exp" : state.get("candidates_exp", empty()),
    }
    return cfg

# ────────────────────────────────────────────────────────
# 2) Solver 실행 래퍼 (UI → 여기만 부르면 됨)
# ────────────────────────────────────────────────────────
def run_solver(cfg: dict, params: dict | None = None, *, debug=False):
    """UI cfg + 파라미터를 solver.solve 로 전달"""
    return solve(cfg, params=params, debug=debug)

# ────────────────────────────────────────────────────────
# 3) DataFrame → Excel(bytes) 변환 (다운로드용)
# ────────────────────────────────────────────────────────
from interview_opt_test_v4 import prepare_schedule   # <- 새로 import!

def to_excel(wide_df: pd.DataFrame) -> bytes:
    pretty = iv4.prepare_schedule(wide_df)

    # 🔍 자동 판단
    by_wave_flag = should_use_wave(pretty)

    buf = BytesIO()
    iv4.df_to_excel(pretty, by_wave=by_wave_flag, stream=buf)
    buf.seek(0)
    return buf.getvalue()
