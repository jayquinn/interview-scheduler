#!/usr/bin/env python3
"""
간단한 UI 엑셀 형식 테스트
"""

import pandas as pd
from datetime import datetime, timedelta, time
import sys
import os

# 필요한 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from solver.api import solve_for_days_v2
    print("✅ 모듈 임포트 성공")
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

def create_simple_config():
    """간단한 설정 생성"""
    
    # 1. 활동 설정
    activities = pd.DataFrame([
        {
            "activity": "토론면접",
            "mode": "batched",
            "duration_min": 30,
            "room_type": "토론면접실",
            "min_cap": 6,
            "max_cap": 6,
            "use": True
        },
        {
            "activity": "발표준비",
            "mode": "parallel",
            "duration_min": 5,
            "room_type": "발표준비실",
            "min_cap": 2,
            "max_cap": 2,
            "use": True
        },
        {
            "activity": "발표면접",
            "mode": "individual",
            "duration_min": 15,
            "room_type": "발표면접실",
            "min_cap": 1,
            "max_cap": 1,
            "use": True
        }
    ])
    
    # 2. 방 설정
    room_plan = pd.DataFrame([{
        "토론면접실_count": 2,
        "토론면접실_cap": 6,
        "발표준비실_count": 1,
        "발표준비실_cap": 2,
        "발표면접실_count": 2,
        "발표면접실_cap": 1
    }])
    
    # 3. 선후행 설정
    precedence = pd.DataFrame([
        {"job_code": "JOB01", "predecessor": "발표준비", "successor": "발표면접", "gap_min": 0}
    ])
    
    # 4. 간단한 1일 계획 (12명)
    base_date = datetime(2024, 7, 1)
    date_plans = {
        "day1": {
            "enabled": True,
            "date": base_date,
            "jobs": [
                {"code": "JOB01", "count": 12}
            ]
        }
    }
    
    return {
        "activities": activities,
        "room_plan": room_plan,
        "precedence": precedence,
        "multidate_plans": date_plans
    }

def test_simple_scheduling():
    """간단한 스케줄링 테스트"""
    print("🧪 간단한 스케줄링 테스트 시작")
    print("=" * 50)
    
    # 1. 설정 생성
    cfg_ui = create_simple_config()
    total_applicants = 12
    
    print(f"📊 테스트 설정:")
    print(f"  - 총 1일간")
    print(f"  - 총 {total_applicants}명 지원자")
    print(f"  - 활동: {len(cfg_ui['activities'])}개")
    
    # 2. 스케줄링 실행
    print(f"\n🚀 CP-SAT 스케줄링 실행...")
    try:
        status, result_df, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
        
        print(f"스케줄링 결과: {status}")
        if status == "SUCCESS":
            print(f"✅ 성공: {len(result_df)}개 스케줄 항목")
            print(f"   지원자 수: {result_df['applicant_id'].nunique()}명")
            print(f"   성공률: {result_df['applicant_id'].nunique()/total_applicants*100:.1f}%")
            
            # 샘플 데이터 출력
            print(f"\n📄 샘플 데이터:")
            print(result_df.head())
            
            return True, result_df
        else:
            print(f"❌ 스케줄링 실패")
            print(f"로그: {logs}")
            return False, None
            
    except Exception as e:
        print(f"❌ 스케줄링 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """메인 실행"""
    print("=" * 50)
    print("🎯 간단한 UI 형식 테스트")
    print("=" * 50)
    
    success, result_df = test_simple_scheduling()
    
    if success:
        print(f"\n🎉 스케줄링 성공!")
        
        # 엑셀 파일 생성 시도
        try:
            from app import df_to_excel
            filename = "simple_test_result.xlsx"
            df_to_excel(result_df, filename)
            print(f"✅ 엑셀 파일 생성 성공: {filename}")
            
            # 파일 크기 확인
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                print(f"   파일 크기: {size:,} bytes")
                
        except Exception as e:
            print(f"❌ 엑셀 파일 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            
    else:
        print(f"\n❌ 스케줄링 실패")
    
    print("=" * 50)

if __name__ == "__main__":
    main() 