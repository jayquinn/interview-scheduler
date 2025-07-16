#!/usr/bin/env python3
"""
5분 단위 라운딩 테스트
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 스케줄러 모듈 import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from solver.api import solve_for_days_v2

def test_5min_rounding():
    """5분 단위 라운딩 테스트"""
    
    # 테스트용 UI 설정
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
            }
        ]),
        "room_plan": pd.DataFrame([
            {
                "date": "2024-01-15",
                "대기실_count": 2,
                "대기실_cap": 1,
                "심층면접실_count": 1,
                "심층면접실_cap": 1
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
                    {"code": "JOB01", "count": 10}
                ]
            }
        }
    }
    
    print("=== 5분 단위 라운딩 테스트 시작 ===")
    
    # 1단계 스케줄링 실행
    status, df, logs, daily_limit = solve_for_days_v2(
        cfg_ui, 
        params={'max_stay_hours': 12},
        debug=True
    )
    
    print(f"스케줄링 상태: {status}")
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
                
                return True
        else:
            print("❌ duration_min 컬럼이 없음")
            return False
    else:
        print(f"❌ 스케줄링 실패: {status}")
        print(f"로그: {logs}")
        return False

def test_manual_rounding():
    """수동 라운딩 테스트"""
    print("\n=== 수동 라운딩 테스트 ===")
    
    # 테스트 케이스들
    test_cases = [
        (166, 165),  # 166분 -> 165분 (5분 단위로 라운딩)
        (167, 165),  # 167분 -> 165분
        (168, 170),  # 168분 -> 170분
        (169, 170),  # 169분 -> 170분
        (170, 170),  # 170분 -> 170분 (이미 5분 단위)
        (165, 165),  # 165분 -> 165분 (이미 5분 단위)
    ]
    
    for input_min, expected in test_cases:
        # 새로운 라운딩 방식
        rounded = int(round(input_min / 5) * 5)
        
        if rounded == expected:
            print(f"✅ {input_min}분 -> {rounded}분 (예상: {expected}분)")
        else:
            print(f"❌ {input_min}분 -> {rounded}분 (예상: {expected}분)")
            return False
    
    return True

if __name__ == "__main__":
    print("5분 단위 라운딩 테스트 시작")
    
    # 수동 라운딩 테스트
    manual_test = test_manual_rounding()
    
    # 실제 스케줄링 테스트
    scheduling_test = test_5min_rounding()
    
    if manual_test and scheduling_test:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n❌ 일부 테스트 실패")
        sys.exit(1) 