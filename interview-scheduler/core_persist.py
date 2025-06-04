# core_persist.py  –  아주 단순한 Pickle 기반 자동 저장
import os, pickle, pandas as pd, streamlit as st
SAVE_PATH = ".autosave.pkl"

def _to_serial(obj):
    """DataFrame → dict, 나머진 그대로"""
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="split")
    return obj

def _from_serial(obj):
    """dict→DataFrame 복원"""
    if isinstance(obj, dict) and \
       {"columns", "index", "data"} <= obj.keys():
        return pd.DataFrame(**obj)
    return obj

def autoload_state():
    """앱 시작 시 파일이 있으면 세션에 로드"""
    if os.path.exists(SAVE_PATH):
        with open(SAVE_PATH, "rb") as f:
            data = pickle.load(f)
        for k, v in data.items():
            if k not in st.session_state:
                st.session_state[k] = _from_serial(v)

def autosave_state():
    """매번 rerun 끝날 때 현재 state 를 파일로 저장"""
    data = {k: _to_serial(v) for k, v in st.session_state.items()
                                   if not k.startswith("_")}
    with open(SAVE_PATH, "wb") as f:
        pickle.dump(data, f)
