from dataclasses import dataclass
from datetime import date
from typing import List

@dataclass
class DailyProjection:
    date: date
    projected_balance: float

@dataclass
class ProjectionResult:
    start_date: date
    end_date: date
    starting_balance: float
    timeline: List[DailyProjection]
    safe_to_spend: float
