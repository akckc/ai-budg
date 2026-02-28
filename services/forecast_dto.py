from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class ForecastDayDTO:
    """Single day in the forecast timeline."""
    date: str  # ISO format YYYY-MM-DD
    projected_balance: float


@dataclass
class ForecastResponseDTO:
    """Complete 14-day forecast response."""
    start_date: str  # ISO format
    end_date: str  # ISO format
    starting_balance: float
    safe_to_spend: float
    timeline: List[ForecastDayDTO]

    @classmethod
    def from_projection(cls, projection):
        """Convert ProjectionResult to JSON-serializable DTO."""
        return cls(
            start_date=projection.start_date.isoformat(),
            end_date=projection.end_date.isoformat(),
            starting_balance=projection.starting_balance,
            safe_to_spend=projection.safe_to_spend,
            timeline=[
                ForecastDayDTO(
                    date=day.date.isoformat(),
                    projected_balance=day.projected_balance
                )
                for day in projection.timeline
            ]
        )
