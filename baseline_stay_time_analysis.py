#!/usr/bin/env python3
"""
베이스라인 체류시간 분석
BALANCED 알고리즘 적용 전 현재 시스템의 체류시간 측정
"""

import pandas as pd
from datetime import timedelta

def analyze_baseline_stay_time():
    """현재 시스템의 체류시간 분석"""
    
    print("📊 베이스라인 체류시간 분석 (BALANCED 적용 전)")
    print("=" * 60)
    
    try:
        # 결과 파일 읽기
        df = pd.read_excel('complete_ui_defaults_test_result.xlsx')
        print(f"✅ 총 {len(df)}개 스케줄 항목 로드")
        
        # 지원자별 체류시간 계산
        applicants = df.groupby('applicant_id').agg({
            'start_time': 'min',
            'end_time': 'max',
            'interview_date': 'first',
            'job_code': 'first'
        }).reset_index()
        
        print(f"✅ 총 {len(applicants)}명 지원자 분석")
        
        # 체류시간 계산 (시간 단위)
        def calculate_stay_hours(row):
            start = row['start_time']
            end = row['end_time']
            
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                # Excel에서 시간이 소수로 저장된 경우 (0.375 = 9:00)
                return (end - start) * 24
            else:
                # 다른 형식의 경우
                return float(str(end)[:2]) - float(str(start)[:2])
        
        applicants['stay_hours'] = applicants.apply(calculate_stay_hours, axis=1)
        
        # 통계 계산
        avg_stay = applicants['stay_hours'].mean()
        max_stay = applicants['stay_hours'].max()
        min_stay = applicants['stay_hours'].min()
        
        # 문제 사례 분석
        long_stay_3h = (applicants['stay_hours'] > 3).sum()
        long_stay_5h = (applicants['stay_hours'] > 5).sum()
        long_stay_6h = (applicants['stay_hours'] > 6).sum()
        
        long_stay_3h_pct = (applicants['stay_hours'] > 3).mean() * 100
        long_stay_5h_pct = (applicants['stay_hours'] > 5).mean() * 100
        long_stay_6h_pct = (applicants['stay_hours'] > 6).mean() * 100
        
        print(f"\n📈 체류시간 통계:")
        print(f"   평균: {avg_stay:.1f}시간")
        print(f"   최대: {max_stay:.1f}시간")
        print(f"   최소: {min_stay:.1f}시간")
        
        print(f"\n⚠️ 문제 사례:")
        print(f"   3시간+ 체류자: {long_stay_3h}명 ({long_stay_3h_pct:.1f}%)")
        print(f"   5시간+ 체류자: {long_stay_5h}명 ({long_stay_5h_pct:.1f}%)")
        print(f"   6시간+ 체류자: {long_stay_6h}명 ({long_stay_6h_pct:.1f}%)")
        
        # 날짜별 분석
        print(f"\n📅 날짜별 체류시간:")
        for date in sorted(applicants['interview_date'].unique()):
            date_data = applicants[applicants['interview_date'] == date]
            date_avg = date_data['stay_hours'].mean()
            date_max = date_data['stay_hours'].max()
            date_long = (date_data['stay_hours'] > 3).sum()
            
            print(f"   {date}: 평균 {date_avg:.1f}h, 최대 {date_max:.1f}h, 3시간+ {date_long}명")
        
        # BALANCED 알고리즘 개선 목표
        print(f"\n🎯 BALANCED 알고리즘 개선 목표:")
        print(f"   현재 평균 체류시간: {avg_stay:.1f}시간")
        print(f"   목표 개선: 2-3시간으로 단축")
        print(f"   예상 효과: {long_stay_3h}명의 체류시간 단축")
        
        return {
            'total_applicants': len(applicants),
            'avg_stay_hours': avg_stay,
            'max_stay_hours': max_stay,
            'long_stay_3h_count': long_stay_3h,
            'long_stay_3h_percent': long_stay_3h_pct
        }
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

if __name__ == "__main__":
    result = analyze_baseline_stay_time()
    if result:
        print(f"\n✅ 베이스라인 분석 완료")
        print(f"   개선 대상: {result['long_stay_3h_count']}명 ({result['long_stay_3h_percent']:.1f}%)")
    else:
        print("❌ 분석 실패") 