# core.py
from io import BytesIO
from datetime import datetime, timedelta
import pandas as pd
from openpyxl import Workbook
import interview_opt_test_v4 as iv4
# OR-Tools 래퍼 ───────────────────────────────────────────
from solver.solver import solve, load_param_grid   # solve()만 쓰면 충분

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
def to_excel(df):
    bio = BytesIO()
    iv4.df_to_excel(df, by_wave=True, stream=bio)  # ★ stream 인자 전달
    return bio.getvalue()
