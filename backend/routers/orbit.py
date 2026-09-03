from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from database import get_db
from models import Satellite

from services.orbit_service import (
    get_satellite_position
)


router = APIRouter(
    prefix="/orbit",
    tags=["Orbit"]
)


# ---------------------------------------------------------
# GET ALL SATELLITE POSITIONS
# ---------------------------------------------------------

@router.get("/positions")
def get_satellite_positions(
    time: str,
    db: Session = Depends(get_db)
):

    try:
        target_time = datetime.fromisoformat(
            time.replace("Z", "+00:00")
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid time format"
        )

    if target_time.tzinfo is None:
        target_time = target_time.replace(
            tzinfo=timezone.utc
        )

    target_time = target_time.astimezone(
        timezone.utc
    )

    satellites = (
        db.query(Satellite)
        .filter(Satellite.is_active == True)
        .all()
    )

    positions = []

    for satellite in satellites:

        try:

            result = get_satellite_position(
                satellite,
                target_time
            )

            positions.append(result)

        except Exception as error:

            print(
                f"Could not calculate "
                f"satellite {satellite.norad_id}: {error}"
            )

    return {
        "time": target_time,
        "count": len(positions),
        "satellites": positions
    }