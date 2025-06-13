"""
유효성 검증 유틸리티 모듈
입력 데이터와 설정의 유효성을 검증합니다.
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional


def validate_activities_data(activities_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    활동 데이터의 유효성을 검증합니다.
    
    Returns:
        Tuple[is_valid, error_messages]
    """
    errors = []
    
    # 필수 컬럼 확인
    required_columns = ['activity', 'mode', 'duration_min', 'room_type', 'min_cap', 'max_cap', 'use']
    missing_columns = [col for col in required_columns if col not in activities_df.columns]
    
    if missing_columns:
        errors.append(f"필수 컬럼이 누락되었습니다: {missing_columns}")
        return False, errors
    
    # 활성화된 활동만 검증
    active_activities = activities_df[activities_df['use'] == True]
    
    if active_activities.empty:
        errors.append("활성화된 활동이 없습니다. 최소 하나 이상의 활동을 활성화해주세요.")
        return False, errors
    
    # 각 활동에 대한 검증
    for idx, row in active_activities.iterrows():
        activity_name = row['activity']
        
        # 활동명 검증
        if pd.isna(activity_name) or activity_name == '':
            errors.append(f"행 {idx}: 활동명이 비어있습니다.")
        
        # 모드 검증
        valid_modes = ['individual', 'parallel', 'batched']
        if row['mode'] not in valid_modes:
            errors.append(f"{activity_name}: 유효하지 않은 모드 '{row['mode']}'. 허용된 모드: {valid_modes}")
        
        # 소요시간 검증
        if pd.isna(row['duration_min']) or row['duration_min'] <= 0:
            errors.append(f"{activity_name}: 소요시간은 0보다 커야 합니다.")
        
        # 방 타입 검증
        if pd.isna(row['room_type']) or row['room_type'] == '':
            errors.append(f"{activity_name}: 면접실 이름이 비어있습니다.")
        
        # 인원 제한 검증
        min_cap = row['min_cap']
        max_cap = row['max_cap']
        
        if pd.isna(min_cap) or min_cap < 1:
            errors.append(f"{activity_name}: 최소 인원은 1명 이상이어야 합니다.")
        
        if pd.isna(max_cap) or max_cap < 1:
            errors.append(f"{activity_name}: 최대 인원은 1명 이상이어야 합니다.")
        
        if not pd.isna(min_cap) and not pd.isna(max_cap) and min_cap > max_cap:
            errors.append(f"{activity_name}: 최소 인원({min_cap})이 최대 인원({max_cap})보다 큽니다.")
        
        # 모드별 추가 검증
        if row['mode'] == 'individual':
            if max_cap != 1:
                errors.append(f"{activity_name}: individual 모드는 최대 인원이 1명이어야 합니다.")
        elif row['mode'] == 'batched':
            if max_cap < 2:
                errors.append(f"{activity_name}: batched 모드는 최대 인원이 2명 이상이어야 합니다.")
    
    # Batched 활동 그룹 크기 호환성 검증
    batched_activities = active_activities[active_activities['mode'] == 'batched']
    if not batched_activities.empty:
        min_caps = batched_activities['min_cap'].values
        max_caps = batched_activities['max_cap'].values
        
        common_min = max(min_caps)
        common_max = min(max_caps)
        
        if common_min > common_max:
            errors.append("Batched 활동들의 그룹 크기가 호환되지 않습니다:")
            for _, act in batched_activities.iterrows():
                errors.append(f"  - {act['activity']}: {act['min_cap']}-{act['max_cap']}명")
            errors.append(f"  공통 범위를 찾을 수 없습니다. (최소: {common_min}, 최대: {common_max})")
    
    return len(errors) == 0, errors


def validate_room_plan(room_plan_df: pd.DataFrame, activities_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    운영 공간 계획의 유효성을 검증합니다.
    
    Returns:
        Tuple[is_valid, error_messages]
    """
    errors = []
    
    if room_plan_df.empty:
        errors.append("운영 공간 계획이 비어있습니다.")
        return False, errors
    
    # 활성화된 활동의 room_type 수집
    active_activities = activities_df[activities_df['use'] == True]
    required_room_types = set(active_activities['room_type'].dropna().unique())
    
    # 각 날짜별로 검증
    for idx, row in room_plan_df.iterrows():
        # 날짜 검증
        if 'date' not in row or pd.isna(row['date']):
            errors.append(f"행 {idx}: 날짜가 지정되지 않았습니다.")
            continue
        
        date_str = str(row['date'])
        
        # 각 room_type별로 검증
        provided_room_types = set()
        
        for col in room_plan_df.columns:
            if col.endswith('_count'):
                room_type = col.replace('_count', '')
                count_col = col
                cap_col = f"{room_type}_cap"
                
                if count_col in row and not pd.isna(row[count_col]) and row[count_col] > 0:
                    provided_room_types.add(room_type)
                    
                    # 용량 검증
                    if cap_col not in row or pd.isna(row[cap_col]) or row[cap_col] <= 0:
                        errors.append(f"{date_str}: {room_type}의 용량이 지정되지 않았거나 0입니다.")
                    
                    # 활동별 최대 인원과 비교
                    if cap_col in row:
                        room_cap = row[cap_col]
                        activities_using_room = active_activities[active_activities['room_type'] == room_type]
                        
                        for _, act in activities_using_room.iterrows():
                            if act['max_cap'] > room_cap:
                                errors.append(
                                    f"{date_str}: {room_type}의 용량({room_cap})이 "
                                    f"{act['activity']} 활동의 최대 인원({act['max_cap']})보다 작습니다."
                                )
        
        # 필수 room_type 확인
        missing_room_types = required_room_types - provided_room_types
        if missing_room_types:
            errors.append(f"{date_str}: 다음 면접실이 설정되지 않았습니다: {missing_room_types}")
    
    return len(errors) == 0, errors


def validate_job_acts_map(job_acts_map_df: pd.DataFrame, activities_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    직무별 면접활동 매핑의 유효성을 검증합니다.
    
    Returns:
        Tuple[is_valid, error_messages]
    """
    errors = []
    
    if job_acts_map_df.empty:
        errors.append("직무별 면접활동 매핑이 비어있습니다.")
        return False, errors
    
    # 필수 컬럼 확인
    if 'code' not in job_acts_map_df.columns:
        errors.append("'code' 컬럼이 없습니다.")
        return False, errors
    
    if 'count' not in job_acts_map_df.columns:
        errors.append("'count' 컬럼이 없습니다.")
        return False, errors
    
    # 활성화된 활동 목록
    active_activities = set(activities_df[activities_df['use'] == True]['activity'].tolist())
    
    # 각 직무별 검증
    for idx, row in job_acts_map_df.iterrows():
        job_code = row['code']
        
        # 직무 코드 검증
        if pd.isna(job_code) or job_code == '':
            errors.append(f"행 {idx}: 직무 코드가 비어있습니다.")
            continue
        
        # 인원수 검증
        if pd.isna(row['count']) or row['count'] <= 0:
            errors.append(f"{job_code}: 인원수는 1명 이상이어야 합니다.")
        
        # 활동 매핑 검증
        mapped_activities = []
        for col in job_acts_map_df.columns:
            if col not in ['code', 'count'] and col in active_activities:
                if row.get(col, False) == True:
                    mapped_activities.append(col)
        
        if not mapped_activities:
            errors.append(f"{job_code}: 매핑된 활동이 없습니다. 최소 하나 이상의 활동을 선택해주세요.")
        
        # Batched 활동 검증
        batched_activities = activities_df[
            (activities_df['use'] == True) & 
            (activities_df['mode'] == 'batched')
        ]['activity'].tolist()
        
        # 모든 직무가 동일한 batched 활동을 가져야 함 (있는 경우)
        if batched_activities:
            missing_batched = set(batched_activities) - set(mapped_activities)
            if missing_batched:
                errors.append(f"{job_code}: 다음 batched 활동이 누락되었습니다: {missing_batched}")
    
    # 중복 직무 코드 검증
    duplicate_codes = job_acts_map_df[job_acts_map_df['code'].duplicated()]['code'].tolist()
    if duplicate_codes:
        errors.append(f"중복된 직무 코드가 있습니다: {duplicate_codes}")
    
    return len(errors) == 0, errors


def validate_precedence_rules(precedence_df: pd.DataFrame, activities_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    선후행 제약 규칙의 유효성을 검증합니다.
    
    Returns:
        Tuple[is_valid, error_messages]
    """
    errors = []
    
    if precedence_df.empty:
        # 선후행 제약은 선택사항이므로 비어있어도 OK
        return True, []
    
    # 필수 컬럼 확인
    required_columns = ['predecessor', 'successor', 'gap_min']
    missing_columns = [col for col in required_columns if col not in precedence_df.columns]
    
    if missing_columns:
        errors.append(f"필수 컬럼이 누락되었습니다: {missing_columns}")
        return False, errors
    
    # 활성화된 활동 목록
    active_activities = set(activities_df[activities_df['use'] == True]['activity'].tolist())
    valid_activities = active_activities | {'__START__', '__END__'}
    
    # 각 규칙 검증
    for idx, row in precedence_df.iterrows():
        pred = row['predecessor']
        succ = row['successor']
        gap = row['gap_min']
        
        # 활동 존재 여부 확인
        if pred not in valid_activities:
            errors.append(f"규칙 {idx}: 선행 활동 '{pred}'가 존재하지 않거나 비활성화되었습니다.")
        
        if succ not in valid_activities:
            errors.append(f"규칙 {idx}: 후행 활동 '{succ}'가 존재하지 않거나 비활성화되었습니다.")
        
        # 순환 참조 방지
        if pred == succ:
            errors.append(f"규칙 {idx}: 같은 활동끼리는 선후행 관계를 설정할 수 없습니다.")
        
        # gap 검증
        if pd.isna(gap) or gap < 0:
            errors.append(f"규칙 {idx}: 최소 간격은 0 이상이어야 합니다.")
    
    # 순환 의존성 검증 (간단한 버전)
    # TODO: 더 정교한 순환 의존성 검증 구현
    
    return len(errors) == 0, errors


def validate_all(config: Dict) -> Tuple[bool, Dict[str, List[str]]]:
    """
    모든 설정의 유효성을 검증합니다.
    
    Args:
        config: 전체 설정 딕셔너리
        
    Returns:
        Tuple[is_valid, error_dict]: 각 섹션별 오류 메시지
    """
    all_errors = {}
    is_valid = True
    
    # 활동 데이터 검증
    if 'activities' in config:
        activities_valid, activities_errors = validate_activities_data(config['activities'])
        if not activities_valid:
            all_errors['activities'] = activities_errors
            is_valid = False
    else:
        all_errors['activities'] = ["활동 데이터가 없습니다."]
        is_valid = False
    
    # 다른 검증은 활동 데이터가 유효한 경우에만 수행
    if 'activities' in config and 'activities' not in all_errors:
        activities_df = config['activities']
        
        # 운영 공간 검증
        if 'room_plan' in config:
            room_valid, room_errors = validate_room_plan(config['room_plan'], activities_df)
            if not room_valid:
                all_errors['room_plan'] = room_errors
                is_valid = False
        
        # 직무별 활동 매핑 검증
        if 'job_acts_map' in config:
            job_valid, job_errors = validate_job_acts_map(config['job_acts_map'], activities_df)
            if not job_valid:
                all_errors['job_acts_map'] = job_errors
                is_valid = False
        
        # 선후행 제약 검증
        if 'precedence' in config:
            prec_valid, prec_errors = validate_precedence_rules(config['precedence'], activities_df)
            if not prec_valid:
                all_errors['precedence'] = prec_errors
                is_valid = False
    
    return is_valid, all_errors 