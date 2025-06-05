# core.py
from io import BytesIO
from datetime import datetime, timedelta
import pandas as pd
from openpyxl import Workbook
import interview_opt_test_v4 as iv4
# OR-Tools 래퍼 ───────────────────────────────────────────
from solver.solver import solve, load_param_grid   # solve()만 쓰면 충분
from interview_opt_test_v4 import prepare_schedule
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

def to_excel(df: pd.DataFrame) -> bytes:
    """
    Streamlit 다운로드용 바이너리 Excel 생성:
      ① prepare_schedule 로 열·행 후처리
      ② df_to_excel 로 컬러 포맷팅 & 저장
    """
    bio = BytesIO()
    df_final = prepare_schedule(df)                  # ★ ① 후처리
    iv4.df_to_excel(df_final, by_wave=True, stream=bio)  # ★ ② 엑셀 작성
    bio.seek(0)
    return bio.getvalue()
