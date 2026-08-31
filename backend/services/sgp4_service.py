from sgp4.api import Satrec


def calculate_position(tle_line1, tle_line2, year, month, day, hour, minute, second):

    satellite = Satrec.twoline2rv(
        tle_line1,
        tle_line2
    )

    # Convert date/time to Julian date
    from sgp4.api import jday

    jd, fr = jday(
        year,
        month,
        day,
        hour,
        minute,
        second
    )

    error_code, position, velocity = satellite.sgp4(
        jd,
        fr
    )

    if error_code != 0:
        raise ValueError(
            f"SGP4 calculation failed with error code {error_code}"
        )

    return {
        "position_km": {
            "x": position[0],
            "y": position[1],
            "z": position[2]
        },
        "velocity_km_s": {
            "x": velocity[0],
            "y": velocity[1],
            "z": velocity[2]
        }
    }