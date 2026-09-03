from datetime import datetime, timezone

from sgp4.api import Satrec, jday


# ---------------------------------------------------------
# CALCULATE SATELLITE POSITION
# ---------------------------------------------------------

def calculate_satellite_position(
    satellite,
    target_time: datetime
):
    """
    Calculate satellite position using SGP4.

    Returns TEME position in km.
    """

    sat = Satrec.twoline2rv(
        satellite.tle_line1,
        satellite.tle_line2
    )

    jd, fr = jday(
        target_time.year,
        target_time.month,
        target_time.day,
        target_time.hour,
        target_time.minute,
        target_time.second
    )

    error_code, position, velocity = sat.sgp4(jd, fr)

    if error_code != 0:
        raise ValueError(
            f"SGP4 calculation failed with error code {error_code}"
        )

    return {
        "x": position[0],
        "y": position[1],
        "z": position[2],
        "vx": velocity[0],
        "vy": velocity[1],
        "vz": velocity[2]
    }


# ---------------------------------------------------------
# JULIAN DATE
# ---------------------------------------------------------

def calculate_julian_date(target_time: datetime):

    jd, fr = jday(
        target_time.year,
        target_time.month,
        target_time.day,
        target_time.hour,
        target_time.minute,
        target_time.second
    )

    return jd + fr


# ---------------------------------------------------------
# GMST
# ---------------------------------------------------------

def calculate_gmst(julian_date):
    """
    Calculate Greenwich Mean Sidereal Time in radians.
    """

    t = (
        julian_date - 2451545.0
    ) / 36525.0

    gmst_degrees = (
        280.46061837
        + 360.98564736629
        * (julian_date - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )

    gmst_degrees %= 360.0

    return gmst_degrees * 3.141592653589793 / 180.0


# ---------------------------------------------------------
# TEME → EARTH FIXED
# ---------------------------------------------------------

def teme_to_ecef(
    x,
    y,
    z,
    target_time
):
    """
    Convert TEME coordinates to an approximate
    Earth-fixed coordinate system.

    Input:
        km

    Output:
        km
    """

    julian_date = calculate_julian_date(
        target_time
    )

    theta = calculate_gmst(
        julian_date
    )

    import math

    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)

    x_ecef = (
        cos_theta * x
        + sin_theta * y
    )

    y_ecef = (
        -sin_theta * x
        + cos_theta * y
    )

    z_ecef = z

    return {
        "x": x_ecef,
        "y": y_ecef,
        "z": z_ecef
    }


# ---------------------------------------------------------
# GET SATELLITE POSITION FOR CESIUM
# ---------------------------------------------------------

def get_satellite_position(
    satellite,
    target_time
):

    position = calculate_satellite_position(
        satellite,
        target_time
    )

    ecef = teme_to_ecef(
        position["x"],
        position["y"],
        position["z"],
        target_time
    )

    return {
        "satellite_id": satellite.id,
        "norad_id": satellite.norad_id,
        "name": satellite.name,

        "position": {
            "x": ecef["x"],
            "y": ecef["y"],
            "z": ecef["z"]
        },

        "velocity": {
            "x": position["vx"],
            "y": position["vy"],
            "z": position["vz"]
        },

        "inclination": satellite.inclination,
        "eccentricity": satellite.eccentricity,
        "raan": satellite.raan,
        "arg_perigee": satellite.arg_perigee,
        "mean_anomaly": satellite.mean_anomaly,
        "mean_motion": satellite.mean_motion
    }