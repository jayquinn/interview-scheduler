#!/usr/bin/env python3
"""
스케줄 데이터 문제 분석 스크립트
group_size와 중복 ID 문제의 원인을 파악합니다.
"""

import pandas as pd
import sys

def analyze_schedule_data():
    """테스트 결과에서 나온 스케줄 데이터를 재실행하여 분석"""
    
    try:
        # 테스트 재실행
        from test_app_default_data import create_app_default_data, test_config_building
        from solver.api import solve_for_days_v2
        
        print("🔧 디폴트 데이터로 재실행...")
        session_state = create_app_default_data()
        
        # Config 빌드
        import core
        cfg = core.build_config(session_state)
        
        # 스케줄러 실행
        params = {
            "min_gap_min": 5,
            "time_limit_sec": 30,
            "max_stay_hours": 5,
            "group_min_size": 4,
            "group_max_size": 6
        }
        
        status, result_df, logs, limit = solve_for_days_v2(cfg, params, debug=True)
        
        if status != "SUCCESS" or result_df is None or result_df.empty:
            print("❌ 스케줄링 실패")
            return
        
        print("✅ 스케줄링 성공: {}개 항목".format(len(result_df)))
        
        # �� 추가: 그룹 생성 과정 상세 분석 (TODO: 변수명 수정 필요)
        # print("\n" + "="*60)
        # print("📊 그룹 생성 과정 상세 분석")
        # print("="*60)
        # 
        # # Level2 결과에서 그룹 정보 추출
        # if hasattr(result, 'results') and result.results:
        #     for date, single_result in result.results.items():
        #         if hasattr(single_result, 'level2_result') and single_result.level2_result:
        #             level2_result = single_result.level2_result
        #             print(f"\n📅 날짜: {date.strftime('%Y-%m-%d')}")
        #             print(f"그룹 결과 수: {len(level2_result.group_results)}")
        #             
        #             for i, group_result in enumerate(level2_result.group_results):
        #                 print(f"\n🎯 활동 {i+1}: {group_result.activity_name}")
        #                 print(f"  - 배정 수: {len(group_result.assignments)}")
        #                 
        #                 for j, assignment in enumerate(group_result.assignments):
        #                     print(f"  - 그룹 {j+1}: {assignment.group.id}")
        #                     print(f"    * 그룹 크기: {assignment.group.size}")
        #                     print(f"    * 실제 지원자 수: {len(assignment.group.applicants)}")
        #                     print(f"    * 더미 ID: {getattr(assignment.group, 'dummy_ids', [])}")
        #                     print(f"    * 방: {assignment.room.name}")
        #                     print(f"    * 시간: {assignment.start_time} ~ {assignment.end_time}")
        #                     
        #                     # 각 지원자 정보
        #                     for k, applicant in enumerate(assignment.group.applicants):
        #                         print(f"      - 지원자 {k+1}: {applicant.id} ({applicant.job_code})")
        
        # 원본 데이터 분석
        print("\n" + "="*60)
        print("📊 원본 스케줄 데이터 분석")
        print("="*60)
        
        print(f"총 항목 수: {len(result_df)}")
        print(f"컬럼: {list(result_df.columns)}")
        print()
        
        # 지원자별 분석
        print("👥 지원자별 분석:")
        applicant_counts = result_df['applicant_id'].value_counts()
        print(f"  - 총 지원자: {len(applicant_counts)}명")
        print(f"  - 지원자별 항목 수: {applicant_counts.values}")
        print()
        
        # 활동별 분석
        print("🎯 활동별 분석:")
        activity_counts = result_df['activity_name'].value_counts()
        for activity, count in activity_counts.items():
            print(f"  - {activity}: {count}개 항목")
        print()
        
        # 방별 분석
        print("🏠 방별 분석:")
        room_counts = result_df['room_name'].value_counts()
        for room, count in room_counts.items():
            print(f"  - {room}: {count}개 항목")
        print()
        
        # 시간별 분석
        print("⏰ 시간별 분석:")
        time_counts = result_df['start_time'].value_counts().sort_index()
        for start_time, count in time_counts.items():
            print(f"  - {start_time}: {count}개 항목")
        print()
        
        # 그룹핑 키 분석 (엑셀 변환에서 사용되는 방식)
        print("🔑 그룹핑 키 분석 (엑셀 변환 방식):")
        result_df['group_key'] = (
            result_df['interview_date'].astype(str) + "_" +
            result_df['activity_name'] + "_" +
            result_df['room_name'] + "_" +
            result_df['start_time'].astype(str)
        )
        
        group_key_counts = result_df['group_key'].value_counts()
        print(f"유니크 그룹 키: {len(group_key_counts)}개")
        print("그룹별 항목 수:")
        for key, count in group_key_counts.head(10).items():
            print(f"  - {key}: {count}개")
        
        if len(group_key_counts) > 10:
            print(f"  ... 및 {len(group_key_counts) - 10}개 더")
        print()
        
        # 시간 중복 확인
        print("🔍 시간 중복 확인:")
        duplicates = result_df.groupby(['applicant_id', 'start_time', 'end_time']).size()
        duplicates = duplicates[duplicates > 1]
        if len(duplicates) > 0:
            print(f"❌ 시간 중복 발견: {len(duplicates)}건")
            for (applicant, start, end), count in duplicates.items():
                print(f"  - {applicant}: {start}~{end} ({count}개 중복)")
        else:
            print("✅ 시간 중복 없음")
        print()
        
        # 활동 종류별 세부 분석
        print("📈 활동별 세부 분석:")
        for activity in result_df['activity_name'].unique():
            activity_df = result_df[result_df['activity_name'] == activity]
            
            print(f"\n{activity}:")
            print(f"  - 총 항목: {len(activity_df)}개")
            print(f"  - 지원자 수: {activity_df['applicant_id'].nunique()}명")
            print(f"  - 방 수: {activity_df['room_name'].nunique()}개")
            print(f"  - 시간 슬롯 수: {activity_df['start_time'].nunique()}개")
            
            # 방별 시간별 분포
            room_time_groups = activity_df.groupby(['room_name', 'start_time']).size()
            print(f"  - 방별/시간별 그룹:")
            for (room, start_time), count in room_time_groups.items():
                print(f"    * {room} {start_time}: {count}명")
        
        # 예상 group_size 계산
        print("\n" + "="*60)
        print("📊 예상 group_size 분석")
        print("="*60)
        
        expected_groups = result_df.groupby(['interview_date', 'activity_name', 'room_name', 'start_time']).size()
        print("날짜/활동/방/시간별 예상 그룹 크기:")
        for (date, activity, room, start_time), size in expected_groups.items():
            print(f"  - {date} {activity} {room} {start_time}: {size}명")
        
        return result_df
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("스케줄 데이터 문제 분석 시작...")
    result = analyze_schedule_data()
    if result is not None:
        print("\n✅ 분석 완료!")
    else:
        print("\n❌ 분석 실패!") 