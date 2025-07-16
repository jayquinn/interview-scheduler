#!/usr/bin/env python3
"""
UI 3단계 스케줄링 5분 단위 라운딩 테스트
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 스케줄러 모듈 import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from solver.api import solve_for_days_three_phase

def test_ui_3phase_5min():
    """UI 3단계 스케줄링 5분 단위 라운딩 테스트"""
    
    # app.py의 기본 설정 사용
    cfg_ui = {
        "activities": pd.DataFrame([
            {
                "use": True,
                "activity": "발표준비",
                "mode": "individual",
                "duration_min": 5,
                "room_type": "대기실",
                "min_cap": 1,
                "max_cap": 1
            },
            {
                "use": True,
                "activity": "발표면접",
                "mode": "individual", 
                "duration_min": 15,
                "room_type": "심층면접실",
                "min_cap": 1,
                "max_cap": 1
            },
            {
                "use": True,
                "activity": "토론면접",
                "mode": "batched",
                "duration_min": 30,
                "room_type": "토론면접실",
                "min_cap": 3,
                "max_cap": 5
            }
        ]),
        "room_plan": pd.DataFrame([
            {
                "date": "2024-01-15",
                "대기실_count": 2,
                "대기실_cap": 1,
                "심층면접실_count": 1,
                "심층면접실_cap": 1,
                "토론면접실_count": 1,
                "토론면접실_cap": 5
            }
        ]),
        "oper_window": pd.DataFrame([
            {
                "code": "JOB01",
                "date": "2024-01-15",
                "start_time": "09:00",
                "end_time": "18:00"
            }
        ]),
        "precedence": pd.DataFrame([
            {
                "predecessor": "발표준비",
                "successor": "발표면접",
                "gap_min": 0,
                "adjacent": True
            }
        ]),
        "multidate_plans": {
            "2024-01-15": {
                "enabled": True,
                "date": "2024-01-15",
                "jobs": [
                    {"code": "JOB01", "count": 15}
                ]
            }
        }
    }
    
    print("=== UI 3단계 스케줄링 5분 단위 라운딩 테스트 시작 ===")
    
    # 3단계 스케줄링 실행
    status, df, logs, daily_limit, reports = solve_for_days_three_phase(
        cfg_ui, 
        params={'max_stay_hours': 12},
        debug=True,
        initial_percentile=90.0,
        final_percentile=90.0,
        max_iterations=1
    )
    
    print(f"3단계 스케줄링 상태: {status}")
    print(f"생성된 스케줄 수: {len(df)}")
    
    if status == "SUCCESS" and not df.empty:
        print("\n=== Duration 분석 ===")
        
        # duration_min 컬럼이 있는지 확인
        if 'duration_min' in df.columns:
            print(f"Duration 컬럼 존재: ✅")
            
            # 5분 단위 여부 확인
            durations = df['duration_min'].values
            non_5min = [d for d in durations if d % 5 != 0]
            
            print(f"총 duration 수: {len(durations)}")
            print(f"5분 단위가 아닌 duration 수: {len(non_5min)}")
            
            if non_5min:
                print(f"5분 단위가 아닌 duration들: {non_5min}")
                print("❌ 5분 단위 라운딩 실패")
                return False
            else:
                print("✅ 모든 duration이 5분 단위")
                
                # duration 분포 확인
                unique_durations = sorted(set(durations))
                print(f"고유 duration 값들: {unique_durations}")
                
                # 종료시간 5분 단위 여부 확인
                print("\n=== 종료시간 5분 단위 분석 ===")
                
                if 'end_time' in df.columns:
                    # end_time을 시간으로 변환
                    end_times = []
                    for end_time in df['end_time']:
                        if isinstance(end_time, timedelta):
                            total_minutes = int(end_time.total_seconds() / 60)
                            end_times.append(total_minutes)
                        elif isinstance(end_time, str):
                            # HH:MM:SS 형식 파싱
                            try:
                                time_parts = end_time.split(':')
                                hours = int(time_parts[0])
                                minutes = int(time_parts[1])
                                total_minutes = hours * 60 + minutes
                                end_times.append(total_minutes)
                            except:
                                end_times.append(0)
                    
                    non_5min_end = [t for t in end_times if t % 5 != 0]
                    print(f"총 종료시간 수: {len(end_times)}")
                    print(f"5분 단위가 아닌 종료시간 수: {len(non_5min_end)}")
                    
                    if non_5min_end:
                        print(f"5분 단위가 아닌 종료시간들: {non_5min_end}")
                        print("❌ 종료시간 5분 단위 라운딩 실패")
                        return False
                    else:
                        print("✅ 모든 종료시간이 5분 단위")
                        
                        # 종료시간 분포 확인
                        unique_end_times = sorted(set(end_times))
                        print(f"고유 종료시간 값들: {unique_end_times}")
                else:
                    print("❌ end_time 컬럼이 없음")
                    return False
                
                return True
        else:
            print("❌ duration_min 컬럼이 없음")
            return False
    else:
        print(f"❌ 3단계 스케줄링 실패: {status}")
        print(f"로그: {logs}")
        return False

if __name__ == "__main__":
    print("UI 3단계 스케줄링 5분 단위 라운딩 테스트 시작")
    
    # 3단계 스케줄링 테스트
    test_result = test_ui_3phase_5min()
    
    if test_result:
        print("\n🎉 3단계 스케줄링 5분 단위 라운딩 테스트 통과!")
    else:
        print("\n❌ 3단계 스케줄링 5분 단위 라운딩 테스트 실패")
        sys.exit(1) 