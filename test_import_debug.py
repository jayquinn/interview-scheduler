#!/usr/bin/env python3
"""
임포트 오류 디버깅 스크립트
"""

print("Step 1: solver module 임포트 테스트")
try:
    import solver
    print("✅ solver module 임포트 성공")
except Exception as e:
    print(f"❌ solver module 임포트 실패: {e}")
    exit(1)

print("Step 2: solver.api 모듈 임포트 테스트")  
try:
    from solver import api
    print("✅ solver.api 모듈 임포트 성공")
except Exception as e:
    print(f"❌ solver.api 모듈 임포트 실패: {e}")
    exit(1)

print("Step 3: solve_for_days_v2 함수 임포트 테스트")
try:
    from solver.api import solve_for_days_v2
    print("✅ solve_for_days_v2 함수 임포트 성공")
except Exception as e:
    print(f"❌ solve_for_days_v2 함수 임포트 실패: {e}")
    exit(1)

print("🎉 모든 임포트 성공!") 