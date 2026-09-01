from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from database import get_db
from models import Satellite

from services.orbit_service import (
    get_orbit_data
)


router = APIRouter(
    prefix="/orbit",
    tags=["Orbit Viewer"]
)


# ---------------------------------------------------------
# GET SATELLITES AVAILABLE FOR ORBIT VIEWER
# ---------------------------------------------------------

@router.get("/satellites")
def get_orbit_satellites(
    db: Session = Depends(get_db)
):

    satellites = (
        db.query(Satellite)
        .filter(
            Satellite.is_active == True
        )
        .all()
    )

    return [
        {
            "id": satellite.id,
            "norad_id": satellite.norad_id,
            "name": satellite.name
        }
        for satellite in satellites
    ]


# ---------------------------------------------------------
# GET ORBIT DATA FOR ONE SATELLITE
# ---------------------------------------------------------

@router.get("/{satellite_id}")
def get_satellite_orbit(
    satellite_id: int,
    start_time: datetime | None = None,
    samples: int = 120,
    db: Session = Depends(get_db)
):

    if samples < 10 or samples > 1000:
        raise HTTPException(
            status_code=400,
            detail="Samples must be between 10 and 1000"
        )

    result = get_orbit_data(
        db,
        satellite_id,
        start_time,
        samples
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Satellite not found"
        )

    return result