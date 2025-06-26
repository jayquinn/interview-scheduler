"""
면접 스케줄링 디버그 헬퍼
실시간 로그 표시, 파일 저장, 실패 원인 분석 기능 제공
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any


class SchedulingDebugHelper:
    """스케줄링 디버그를 위한 헬퍼 클래스"""
    
    def __init__(self, log_dir: str = "log"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_log_file = None
        self.log_messages = []
        
    def start_session(self, config: Dict[str, Any]) -> str:
        """새로운 디버그 세션 시작"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"schedule_debug_{timestamp}.json"
        self.current_log_file = self.log_dir / log_filename
        
        # 초기 로그 정보
        session_info = {
            "timestamp": timestamp,
            "config": self._serialize_config(config),
            "logs": []
        }
        
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            json.dump(session_info, f, ensure_ascii=False, indent=2)
            
        return str(self.current_log_file)
    
    def _serialize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """설정을 JSON 직렬화 가능한 형태로 변환"""
        serialized = {}
        for key, value in config.items():
            if isinstance(value, pd.DataFrame):
                serialized[key] = {
                    "type": "DataFrame",
                    "shape": value.shape,
                    "data": value.to_dict('records')
                }
            elif hasattr(value, '__dict__'):
                serialized[key] = str(value)
            else:
                serialized[key] = value
        return serialized
    
    def log(self, level: str, message: str, data: Optional[Dict] = None):
        """로그 메시지 추가"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data or {}
        }
        
        self.log_messages.append(log_entry)
        
        # 파일에 즉시 기록
        if self.current_log_file and self.current_log_file.exists():
            with open(self.current_log_file, 'r+', encoding='utf-8') as f:
                session_data = json.load(f)
                session_data["logs"].append(log_entry)
                f.seek(0)
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                f.truncate()
    
    def analyze_failure(self, status: str, logs: str):
        """실패 원인 분석 및 해결책 제시"""
        st.error(f"❌ 스케줄링 실패: {status}")
        
        # 패턴 기반 분석
        patterns = {
            "NO_SOLUTION": {
                "keywords": ["모든 지원자를 배정하지 못했습니다"],
                "cause": "제약 조건이 너무 엄격하여 모든 지원자를 배정할 수 없음",
                "solutions": [
                    "운영 시간을 늘리기 (예: 9-18시 → 9-19시)",
                    "운영 공간(방) 개수 늘리기",
                    "활동 소요시간 단축",
                    "선후행 제약 완화 (adjacent → 일반 순서)"
                ]
            },
            "INFEASIBLE": {
                "keywords": ["INFEASIBLE", "no feasible solution"],
                "cause": "현재 설정으로는 스케줄을 만들 수 없음",
                "solutions": [
                    "체류시간 제한 늘리기",
                    "활동 간 최소 간격(gap) 줄이기",
                    "동시 수용 인원(capacity) 늘리기"
                ]
            },
            "ADJACENT_CONFLICT": {
                "keywords": ["adjacent", "batched", "parallel", "individual"],
                "cause": "Batched/Parallel → Individual adjacent 제약이 구조적으로 불가능",
                "solutions": [
                    "Adjacent 제약을 일반 순서 제약으로 변경",
                    "Individual 활동의 방 개수를 그룹 크기만큼 증설",
                    "그룹 크기를 Individual 방 개수에 맞춰 축소",
                    "Parallel 활동의 수용 인원을 Individual 방 개수에 맞춰 조정"
                ]
            },
            "TIME_LIMIT": {
                "keywords": ["시간 초과", "time limit", "timeout"],
                "cause": "계산 시간 초과",
                "solutions": [
                    "일일 처리 인원 줄이기",
                    "시간 제한 늘리기 (params['time_limit_sec'])",
                    "제약 조건 단순화"
                ]
            }
        }
        
        # Adjacent 체인 분석 추가
        if "adjacent" in logs.lower() and ("batched" in logs or "parallel" in logs):
            st.warning("⚠️ 복잡한 Adjacent 체인 감지됨")
            st.markdown("""
            **Batched/Parallel → Individual Adjacent 문제**
            - 그룹으로 활동한 사람들이 개별 활동으로 즉시 전환해야 하는 구조
            - 예: 6명 그룹 → 2명씩 parallel → 1명씩 individual
            - 이런 경우 병목 현상이 발생하여 스케줄링이 불가능할 수 있습니다.
            """)
        
        # 로그에서 패턴 찾기
        detected_patterns = []
        for pattern_name, pattern_info in patterns.items():
            if any(keyword in logs for keyword in pattern_info["keywords"]):
                detected_patterns.append((pattern_name, pattern_info))
        
        if detected_patterns:
            st.markdown("### 🔍 원인 분석")
            for pattern_name, pattern_info in detected_patterns:
                st.info(f"**{pattern_info['cause']}**")
                
            st.markdown("### 💡 해결 방안")
            all_solutions = set()
            for _, pattern_info in detected_patterns:
                all_solutions.update(pattern_info['solutions'])
            
            for i, solution in enumerate(all_solutions, 1):
                st.markdown(f"{i}. {solution}")
        else:
            st.markdown("### 🔍 일반적인 해결 방안")
            st.markdown("""
            1. 제약 조건 검토 및 완화
            2. 운영 자원(시간, 공간) 확대
            3. 활동 구성 단순화
            4. 일일 처리 인원 조정
            """)
    
    def display_realtime_logs(self, container=None):
        """실시간 로그 표시 (Streamlit)"""
        if container is None:
            container = st.container()
            
        with container:
            if self.log_messages:
                st.subheader("📋 실시간 로그")
                
                # 최근 로그부터 표시
                for log in reversed(self.log_messages[-50:]):  # 최근 50개만
                    level = log["level"]
                    message = log["message"]
                    timestamp = log["timestamp"].split("T")[1].split(".")[0]  # 시간만 표시
                    
                    # 레벨별 색상
                    if level == "ERROR":
                        st.error(f"[{timestamp}] {message}")
                    elif level == "WARNING":
                        st.warning(f"[{timestamp}] {message}")
                    elif level == "INFO":
                        st.info(f"[{timestamp}] {message}")
                    else:
                        st.text(f"[{timestamp}] {message}")
                        
                    # 추가 데이터가 있으면 표시
                    if log.get("data"):
                        with st.expander("상세 정보"):
                            st.json(log["data"])
    
    def save_failure_analysis(self, analysis: Dict[str, Any]):
        """실패 분석 결과 저장"""
        if self.current_log_file and self.current_log_file.exists():
            with open(self.current_log_file, 'r+', encoding='utf-8') as f:
                session_data = json.load(f)
                session_data["failure_analysis"] = analysis
                f.seek(0)
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                f.truncate()
    
    def get_log_files(self) -> List[Path]:
        """저장된 로그 파일 목록 반환"""
        return sorted(self.log_dir.glob("schedule_debug_*.json"), reverse=True)
    
    def load_log_file(self, filename: str) -> Dict[str, Any]:
        """로그 파일 로드"""
        filepath = self.log_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}


def create_debug_summary(config: Dict[str, Any], status: str, logs: str) -> str:
    """디버그 요약 정보 생성"""
    summary = []
    summary.append(f"상태: {status}")
    summary.append(f"타임스탬프: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 주요 설정 정보
    if "activities" in config:
        activities_df = config["activities"]
        if isinstance(activities_df, pd.DataFrame):
            summary.append(f"활동 수: {len(activities_df[activities_df['use'] == True])}")
            
            # 모드별 활동 수
            if 'mode' in activities_df.columns:
                mode_counts = activities_df[activities_df['use'] == True]['mode'].value_counts()
                for mode, count in mode_counts.items():
                    summary.append(f"  - {mode}: {count}개")
    
    if "job_acts_map" in config:
        job_df = config["job_acts_map"]
        if isinstance(job_df, pd.DataFrame):
            summary.append(f"직무 수: {len(job_df)}")
            summary.append(f"총 지원자: {job_df['count'].sum()}명")
    
    if "precedence" in config:
        prec_df = config["precedence"]
        if isinstance(prec_df, pd.DataFrame):
            summary.append(f"선후행 제약: {len(prec_df)}개")
            if 'adjacent' in prec_df.columns:
                adj_count = len(prec_df[prec_df['adjacent'] == True])
                if adj_count > 0:
                    summary.append(f"  - 연속 배치: {adj_count}개")
    
    # 로그에서 핵심 정보 추출
    if "INFEASIBLE" in logs:
        summary.append("\n⚠️ 해결 불가능한 제약 조건이 있습니다.")
    elif "NO_SOLUTION" in logs:
        summary.append("\n⚠️ 주어진 기간 내에 모든 지원자를 배정할 수 없습니다.")
    
    return "\n".join(summary)

def create_debug_ui():
    """디버그 UI 컴포넌트 생성"""
    with st.expander("🐛 디버그 옵션", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            debug_mode = st.checkbox("디버그 모드", key="debug_mode_checkbox")
            save_logs = st.checkbox("로그 파일 저장", key="save_logs_checkbox", value=True)
        
        with col2:
            show_realtime = st.checkbox("실시간 로그 표시", key="show_realtime_checkbox")
            show_details = st.checkbox("상세 정보 표시", key="show_details_checkbox")
        
        with col3:
            log_level = st.selectbox(
                "로그 레벨",
                ["INFO", "DEBUG", "WARNING", "ERROR"],
                key="log_level_select"
            )
        
        return {
            "debug_mode": debug_mode,
            "save_logs": save_logs,
            "show_realtime": show_realtime,
            "show_details": show_details,
            "log_level": log_level
        }

def display_failure_analysis(analysis: Dict[str, Any]):
    """실패 분석 결과 표시"""
    st.error(f"❌ 스케줄링 실패: {analysis['status']}")
    
    if analysis["possible_causes"]:
        st.markdown("### 🔍 가능한 원인")
        for cause in analysis["possible_causes"]:
            st.markdown(f"- {cause}")
    
    if analysis["suggestions"]:
        st.markdown("### 💡 해결 방안")
        for suggestion in analysis["suggestions"]:
            st.markdown(f"- {suggestion}")
    
    # 로그 다운로드 링크
    if st.session_state.get("debug_helper"):
        helper = st.session_state["debug_helper"]
        log_content = "\n".join(helper.logs)
        st.download_button(
            "📥 전체 로그 다운로드",
            log_content,
            file_name=f"debug_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        ) 