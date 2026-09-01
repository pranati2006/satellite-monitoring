from datetime import datetime, timedelta, timezone
import math

from models import Satellite
from services.sgp4_service import calculate_position


# ---------------------------------------------------------
# CALCULATE ORBIT PERIOD
# ---------------------------------------------------------

def calculate_orbit_period(mean_motion):
    """
    mean_motion = revolutions per day

    Returns orbital period in seconds.
    """

    if not mean_motion or mean_motion <= 0:
        return None

    return 86400 / mean_motion


# ---------------------------------------------------------
# GET CURRENT POSITION
# ---------------------------------------------------------

def get_current_position(
    satellite: Satellite
):

    current_time = datetime.now(timezone.utc)

    result = calculate_position(
        satellite.tle_line1,
        satellite.tle_line2,
        current_time.year,
        current_time.month,
        current_time.day,
        current_time.hour,
        current_time.minute,
        current_time.second
    )

    return {
        "timestamp": current_time,
        "position": result["position_km"],
        "velocity": result["velocity_km_s"]
    }


# ---------------------------------------------------------
# GENERATE ORBIT PATH
# ---------------------------------------------------------

def generate_orbit_path(
    satellite: Satellite,
    start_time: datetime | None = None,
    samples: int = 120
):

    if start_time is None:
        start_time = datetime.now(timezone.utc)

    if start_time.tzinfo is None:
        start_time = start_time.replace(
            tzinfo=timezone.utc
        )

    period_seconds = calculate_orbit_period(
        satellite.mean_motion
    )

    if period_seconds is None:
        raise ValueError(
            "Invalid satellite mean motion"
        )

    interval_seconds = period_seconds / samples

    positions = []

    for i in range(samples):

        current_time = (
            start_time
            + timedelta(
                seconds=i * interval_seconds
            )
        )

        result = calculate_position(
            satellite.tle_line1,
            satellite.tle_line2,
            current_time.year,
            current_time.month,
            current_time.day,
            current_time.hour,
            current_time.minute,
            current_time.second
        )

        positions.append({
            "timestamp": current_time,
            "position": result["position_km"]
        })

    return {
        "orbit_period_seconds": period_seconds,
        "positions": positions
    }


# ---------------------------------------------------------
# GET ORBIT DATA FOR ONE SATELLITE
# ---------------------------------------------------------

def get_orbit_data(
    db,
    satellite_id: int,
    start_time: datetime | None = None,
    samples: int = 120
):

    satellite = (
        db.query(Satellite)
        .filter(
            Satellite.id == satellite_id
        )
        .first()
    )

    if satellite is None:
        return None

    current_position = get_current_position(
        satellite
    )

    orbit = generate_orbit_path(
        satellite,
        start_time=start_time,
        samples=samples
    )

    return {
        "satellite_id": satellite.id,
        "norad_id": satellite.norad_id,
        "name": satellite.name,

        "current_position": current_position,

        "orbit_period_seconds":
            orbit["orbit_period_seconds"],

        "orbit_path":
            orbit["positions"]
    }