from fastapi import APIRouter, Query
from datetime import date
from typing import Optional
from services.projection_service import calculate_two_week_projection
from services.forecast_dto import ForecastResponseDTO

router = APIRouter()


@router.get("/forecast")
def get_14_day_forecast(as_of_date: Optional[str] = Query(None)):
    """
    Return a deterministic 14-day projection of account balances.

    Query Parameters:
        as_of_date (optional): Reference date in ISO format (YYYY-MM-DD).
                              Defaults to today if not provided.

    Returns:
        ForecastResponseDTO: JSON containing daily balance timeline and Safe-to-Spend.

    Deterministic, read-only, multi-account aware.
    """
    # Parse optional as_of_date parameter
    if as_of_date:
        try:
            as_of = date.fromisoformat(as_of_date)
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}
    else:
        as_of = None

    try:
        # Compute projection using deterministic engine
        projection = calculate_two_week_projection(as_of_date=as_of)

        # Convert to JSON-serializable DTO
        dto = ForecastResponseDTO.from_projection(projection)

        # Return as dict so FastAPI can serialize to JSON
        return {
            "start_date": dto.start_date,
            "end_date": dto.end_date,
            "starting_balance": dto.starting_balance,
            "safe_to_spend": dto.safe_to_spend,
            "timeline": [
                {"date": day.date, "projected_balance": day.projected_balance}
                for day in dto.timeline
            ]
        }
    except Exception as e:
        return {"error": str(e)}
