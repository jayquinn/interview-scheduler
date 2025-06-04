# core.py
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
def build_config(state: dict) -> dict:
    """
    Streamlit 세션 state 딕셔너리를
    run_solver 에 넘길 하나의 dict로 합쳐 준다.
    (필수 키가 없으면 기본 빈 DataFrame 넣기)
    """
    def _empty_df():
        return pd.DataFrame()

    cfg = {
        "activities"  : state.get("activities",  _empty_df()),
        "room_plan"   : state.get("room_plan",   _empty_df()),
        "oper_window" : state.get("oper_window", _empty_df()),
        "precedence"  : state.get("precedence",  _empty_df()),
        "candidates"      : state.get("candidates",      _empty_df()),
        "candidates_exp"  : state.get("candidates_exp",  _empty_df()),
    }
    return cfg
def run_solver(cfg: dict):
    """
    - 09:00 시작
    - 활동 표(activities) 순서대로 진행
    - 한 지원자 끝나면 다음 지원자
    """
    cand = cfg["candidates_exp"]
    acts = cfg["activities"]
    if cand is None or acts is None or cand.empty or acts.empty:
        return "NO_DATA", None
    cand["interview_date"] = pd.to_datetime(cand["interview_date"]).dt.date
    acts = acts.query("use == True").reset_index(drop=True)
    rows = []
    t0 = datetime.combine(cand["interview_date"].min(), datetime.min.time()) + timedelta(hours=9)

    for idx, (cid, grp) in enumerate(cand.groupby("id")):
        cur = t0 + idx * timedelta(minutes=10 * len(acts))
        for _, a in acts.iterrows():
            start = cur
            end   = start + timedelta(minutes=a.duration_min)
            rows.append({
                "id": cid,
                "activity": a.activity,
                "start": start,
                "end":   end,
                "loc": f"{a.room_type}01",
            })
            cur = end

    long = pd.DataFrame(rows)
    wide = (long
            .pivot(index="id", columns="activity", values=["loc","start","end"])
            .reset_index())
    wide.columns = ["_".join(c).strip("_") for c in wide.columns]
    return "OK", wide

def to_excel(df: pd.DataFrame) -> bytes:
    from io import BytesIO
    bio = BytesIO()
    df.to_excel(bio, index=False, engine="openpyxl")
    bio.seek(0)
    return bio.getvalue()
