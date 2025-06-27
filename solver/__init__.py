"""
면접 스케줄링 시스템
"""

from .api import (
    schedule_interviews,
    convert_to_wide_format,
    create_default_global_config,
    create_date_plan
)

from .types import (
    ActivityMode,
    Activity,
    Room,
    Applicant,
    Group,
    TimeSlot,
    ScheduleItem,
    PrecedenceRule,
    GlobalConfig,
    DatePlan,
    DateConfig,
    MultiDateResult,
    SingleDateResult
)

__all__ = [
    # Main API
    'schedule_interviews',
    'convert_to_wide_format',
    'create_default_global_config',
    'create_date_plan',
    
    # Types
    'ActivityMode',
    'Activity',
    'Room', 
    'Applicant',
    'Group',
    'TimeSlot',
    'ScheduleItem',
    'PrecedenceRule',
    'GlobalConfig',
    'DatePlan',
    'DateConfig',
    'MultiDateResult',
    'SingleDateResult'
]

__version__ = '2.0.0' 