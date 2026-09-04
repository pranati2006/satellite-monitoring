from datetime import datetime, timedelta
from collections import defaultdict
from math import atan2, degrees, floor, sqrt, sin, cos, pi

from services.sgp4_service import calculate_position


# =========================================================
# CONFIGURATION
# =========================================================

EARTH_RADIUS_KM = 6378.137

# Altitude bucket size
ALTITUDE_BAND_SIZE_KM = 100

# Temporal hash bucket size
TIME_BUCKET_SECONDS = 300  # 5 minutes

# Spatial grid size
GRID_CELL_SIZE_DEG = 5.0

# Only used while learning the altitude pattern
# from ONE orbital revolution.
PROPAGATION_STEP_SECONDS = 30


# =========================================================
# 1. PHYSICS / COORDINATE HELPERS
# =========================================================

def calculate_altitude(position):
    """
    Calculate altitude above Earth's mean radius.
    """

    x = float(position["x"])
    y = float(position["y"])
    z = float(position["z"])

    radius = sqrt(x * x + y * y + z * z)

    return radius - EARTH_RADIUS_KM


def calculate_latitude_longitude(position, timestamp):
    """
    Convert ECI position to approximate latitude/longitude
    using Earth rotation.
    """

    x = float(position["x"])
    y = float(position["y"])
    z = float(position["z"])

    seconds_since_epoch = timestamp.timestamp()

    earth_rotation_angle = (
        seconds_since_epoch * 7.2921159e-5
    ) % (2 * pi)

    cos_angle = cos(earth_rotation_angle)
    sin_angle = sin(earth_rotation_angle)

    x_ecef = cos_angle * x + sin_angle * y
    y_ecef = -sin_angle * x + cos_angle * y

    longitude = degrees(
        atan2(y_ecef, x_ecef)
    )

    latitude = degrees(
        atan2(
            z,
            sqrt(
                x_ecef * x_ecef +
                y_ecef * y_ecef
            )
        )
    )

    return {
        "latitude": latitude,
        "longitude": longitude
    }


def get_position(satellite, timestamp):
    """
    Run SGP4 for one satellite at one timestamp.
    """

    try:
        result = calculate_position(
            satellite["tle_line1"],
            satellite["tle_line2"],
            timestamp.year,
            timestamp.month,
            timestamp.day,
            timestamp.hour,
            timestamp.minute,
            timestamp.second
        )

    except (ValueError, TypeError):
        return None

    if result is None:
        return None

    return result["position_km"]


def get_position_and_altitude(satellite, timestamp):
    """
    SGP4 position + altitude.

    Used ONLY while learning the altitude pattern
    during one orbital revolution.
    """

    position = get_position(satellite, timestamp)

    if position is None:
        return None

    altitude = calculate_altitude(position)

    return {
        "timestamp": timestamp,
        "altitude": altitude
    }


def get_altitude_band_key(altitude):
    """
    Example:

    1534 km -> 1500
    1598 km -> 1500
    1620 km -> 1600
    """

    return (
        floor(altitude / ALTITUDE_BAND_SIZE_KM)
        * ALTITUDE_BAND_SIZE_KM
    )


def get_orbital_period_seconds(satellite):
    """
    mean_motion is revolutions/day.

    period = 86400 / revolutions_per_day
    """

    mean_motion = float(satellite["mean_motion"])

    if mean_motion <= 0:
        return None

    return 86400.0 / mean_motion


# =========================================================
# 2. LEARN ONE ORBITAL REVOLUTION
# =========================================================

def extract_one_orbit_altitude_intervals(
    satellite,
    start_time
):
    """
    Propagate ONE orbital revolution.

    The purpose here is NOT to create the final
    7-day trajectory.

    We only learn:

        altitude band
             +
        time interval

    for one revolution.

    These intervals are later repeated using
    the satellite's orbital period.
    """

    period_seconds = get_orbital_period_seconds(
        satellite
    )

    if period_seconds is None:
        return []

    end_time = (
        start_time +
        timedelta(seconds=period_seconds)
    )

    intervals = []

    current_time = start_time
    current_band = None
    current_start_time = None

    while current_time <= end_time:

        point = get_position_and_altitude(
            satellite,
            current_time
        )

        if point is not None:

            band = get_altitude_band_key(
                point["altitude"]
            )

            # First point
            if current_band is None:

                current_band = band
                current_start_time = (
                    point["timestamp"]
                )

            # Still inside same altitude band
            elif band == current_band:

                pass

            # Altitude band changed
            else:

                if current_start_time is not None:

                    intervals.append({
                        "satellite": satellite,

                        "altitude_start": current_band,

                        "altitude_end":
                            current_band +
                            ALTITUDE_BAND_SIZE_KM,

                        "start_offset":
                            current_start_time - start_time,

                        "end_offset":
                            point["timestamp"] - start_time
                    })

                current_band = band

                current_start_time = (
                    point["timestamp"]
                )

        current_time += timedelta(
            seconds=PROPAGATION_STEP_SECONDS
        )

    # Flush final interval
    if (
        current_band is not None
        and current_start_time is not None
    ):

        intervals.append({
            "satellite": satellite,

            "altitude_start": current_band,

            "altitude_end":
                current_band +
                ALTITUDE_BAND_SIZE_KM,

            "start_offset":
                current_start_time - start_time,

            "end_offset":
                end_time - start_time
        })

    return intervals


# =========================================================
# 3. REPEAT INTERVALS FOR THE WHOLE PREDICTION WINDOW
# =========================================================

def generate_7_day_intervals(
    satellite,
    one_orbit_intervals,
    start_time,
    end_time
):
    """
    Take the altitude/time pattern learned from
    ONE orbit and repeat it using orbital period
    until the requested prediction end time.

    No additional SGP4 is performed here.
    """

    period_seconds = get_orbital_period_seconds(
        satellite
    )

    if period_seconds is None:
        return []

    period = timedelta(
        seconds=period_seconds
    )

    generated = []

    revolution_start = start_time

    while revolution_start <= end_time:

        for interval in one_orbit_intervals:

            interval_start = (
                revolution_start +
                interval["start_offset"]
            )

            interval_end = (
                revolution_start +
                interval["end_offset"]
            )

            # Ignore intervals completely outside
            # requested prediction window.
            if interval_end < start_time:
                continue

            if interval_start > end_time:
                continue

            # Clip to requested window
            clipped_start = max(
                interval_start,
                start_time
            )

            clipped_end = min(
                interval_end,
                end_time
            )

            if clipped_start <= clipped_end:

                generated.append({
                    "satellite":
                        satellite,

                    "altitude_start":
                        interval[
                            "altitude_start"
                        ],

                    "altitude_end":
                        interval[
                            "altitude_end"
                        ],

                    "start_time":
                        clipped_start,

                    "end_time":
                        clipped_end
                })

        revolution_start += period

    return generated


# =========================================================
# 4. LAT/LON FOR INTERVAL ENDPOINTS
# =========================================================

def add_spatial_information(interval):
    """
    Calculate latitude/longitude ONLY at the
    start and end of the interval.

    These are the only extra SGP4 calculations
    needed after the altitude/time filtering stage.
    """

    satellite = interval["satellite"]

    start_position = get_position(
        satellite,
        interval["start_time"]
    )

    end_position = get_position(
        satellite,
        interval["end_time"]
    )

    if start_position is None or end_position is None:
        return None

    start_lat_lon = calculate_latitude_longitude(
        start_position,
        interval["start_time"]
    )

    end_lat_lon = calculate_latitude_longitude(
        end_position,
        interval["end_time"]
    )

    points = [
        start_lat_lon,
        end_lat_lon
    ]

    interval["start_latitude"] = (
        start_lat_lon["latitude"]
    )

    interval["start_longitude"] = (
        start_lat_lon["longitude"]
    )

    interval["end_latitude"] = (
        end_lat_lon["latitude"]
    )

    interval["end_longitude"] = (
        end_lat_lon["longitude"]
    )

    interval["square"] = create_square(points)

    return interval


# =========================================================
# 5. BOUNDING SQUARE
# =========================================================

def create_square(points):
    """
    Create a conservative bounding rectangle from
    interval start/end coordinates.
    """

    min_lat = min(
        point["latitude"]
        for point in points
    )

    max_lat = max(
        point["latitude"]
        for point in points
    )

    longitudes = [
        point["longitude"]
        for point in points
    ]

    # Near poles: longitude becomes unreliable.
    if (
        max_lat > 80.0
        or min_lat < -80.0
    ):

        return {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": -180.0,
            "max_lon": 180.0,
            "crosses_antimeridian": False
        }

    crosses_antimeridian = (
        len(longitudes) >= 2
        and abs(
            longitudes[1] -
            longitudes[0]
        ) > 180.0
    )

    if crosses_antimeridian:

        negative = [
            lon
            for lon in longitudes
            if lon < 0
        ]

        positive = [
            lon
            for lon in longitudes
            if lon >= 0
        ]

        min_lon = (
            max(negative)
            if negative
            else -180.0
        )

        max_lon = (
            min(positive)
            if positive
            else 180.0
        )

    else:

        min_lon = min(longitudes)
        max_lon = max(longitudes)

    return {
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lon": min_lon,
        "max_lon": max_lon,
        "crosses_antimeridian":
            crosses_antimeridian
    }


# =========================================================
# 6. ALTITUDE + TIME HASH
# =========================================================

def get_time_bucket(timestamp):
    """
    Convert timestamp into a 5-minute bucket.

    Example:

        10:02 -> 10:00 bucket
        10:04 -> 10:00 bucket
        10:07 -> 10:05 bucket
    """

    unix_seconds = int(
        timestamp.timestamp()
    )

    bucket = (
        unix_seconds //
        TIME_BUCKET_SECONDS
    )

    return bucket


def get_altitude_time_hash_key(interval):
    """
    Main screening hash:

        altitude band + time bucket
    """

    return (
        interval["altitude_start"],
        get_time_bucket(
            interval["start_time"]
        )
    )


def build_altitude_time_hash(intervals):
    """
    Put intervals into a hash table.

    This prevents O(N²) comparison across
    completely unrelated intervals.
    """

    interval_hash = defaultdict(list)

    for interval in intervals:

        start_bucket = get_time_bucket(
            interval["start_time"]
        )

        end_bucket = get_time_bucket(
            interval["end_time"]
        )

        altitude_band = (
            interval["altitude_start"]
        )

        # An interval can span multiple
        # time buckets, so insert it into
        # every bucket it touches.
        for bucket in range(
            start_bucket,
            end_bucket + 1
        ):

            interval_hash[
                (altitude_band, bucket)
            ].append(interval)

    return interval_hash


# =========================================================
# 7. BASIC INTERVAL OVERLAP
# =========================================================

def altitude_overlap(inv1, inv2):
    return not (
        inv1["altitude_end"]
        < inv2["altitude_start"]
        or
        inv2["altitude_end"]
        < inv1["altitude_start"]
    )


def time_overlap(inv1, inv2):
    return not (
        inv1["end_time"]
        < inv2["start_time"]
        or
        inv2["end_time"]
        < inv1["start_time"]
    )


def spatial_overlap(inv1, inv2):
    square1 = inv1["square"]
    square2 = inv2["square"]

    # Latitude
    if (
        square1["max_lat"]
        < square2["min_lat"]
        or
        square2["max_lat"]
        < square1["min_lat"]
    ):
        return False

    # If neither crosses anti-meridian,
    # perform normal longitude test.
    if (
        not square1.get(
            "crosses_antimeridian",
            False
        )
        and
        not square2.get(
            "crosses_antimeridian",
            False
        )
    ):

        if (
            square1["max_lon"]
            < square2["min_lon"]
            or
            square2["max_lon"]
            < square1["min_lon"]
        ):
            return False

        return True

    # Conservative result when either
    # square crosses anti-meridian.
    return True


def intervals_overlap(inv1, inv2):
    """
    Final interval overlap test.
    """

    if not altitude_overlap(
        inv1,
        inv2
    ):
        return False

    if not time_overlap(
        inv1,
        inv2
    ):
        return False

    if not spatial_overlap(
        inv1,
        inv2
    ):
        return False

    return True


# =========================================================
# 8. SPATIAL HASH
# =========================================================

def get_grid_cells(square):
    """
    Convert a square into 5° spatial hash cells.
    """

    min_lat_cell = floor(
        square["min_lat"]
        / GRID_CELL_SIZE_DEG
    )

    max_lat_cell = floor(
        square["max_lat"]
        / GRID_CELL_SIZE_DEG
    )

    min_lon_cell = floor(
        square["min_lon"]
        / GRID_CELL_SIZE_DEG
    )

    max_lon_cell = floor(
        square["max_lon"]
        / GRID_CELL_SIZE_DEG
    )

    cells = []

    if not square.get(
        "crosses_antimeridian",
        False
    ):

        for lat_cell in range(
            min_lat_cell,
            max_lat_cell + 1
        ):

            for lon_cell in range(
                min_lon_cell,
                max_lon_cell + 1
            ):

                cells.append(
                    (lat_cell, lon_cell)
                )

    else:

        max_lon_bin = (
            floor(
                180.0 /
                GRID_CELL_SIZE_DEG
            ) - 1
        )

        min_lon_bin = floor(
            -180.0 /
            GRID_CELL_SIZE_DEG
        )

        lon_ranges = [
            range(
                min_lon_cell,
                max_lon_bin + 1
            ),
            range(
                min_lon_bin,
                max_lon_cell + 1
            )
        ]

        for lat_cell in range(
            min_lat_cell,
            max_lat_cell + 1
        ):

            for lon_range in lon_ranges:

                for lon_cell in lon_range:

                    cells.append(
                        (lat_cell, lon_cell)
                    )

    return cells


# =========================================================
# 9. FINAL BATCHING
# =========================================================

def build_altitude_time_bins(intervals):
    """
    Put intervals into ONE bin for each:
        altitude band + 5-minute time bucket

    No spatial cells yet.
    """

    bins = defaultdict(list)

    for interval in intervals:

        altitude_band = interval["altitude_start"]

        start_bucket = get_time_bucket(
            interval["start_time"]
        )

        end_bucket = get_time_bucket(
            interval["end_time"]
        )

        for time_bucket in range(
            start_bucket,
            end_bucket + 1
        ):

            key = (
                altitude_band,
                time_bucket
            )

            bins[key].append(interval)

    return bins


def group_intervals_into_batches(intervals):

    bins = build_altitude_time_bins(intervals)

    print(
        f"Total altitude/time bins: {len(bins)}"
    )

    batches = []

    for key, bin_intervals in bins.items():

        # Get unique satellites in this bin
        unique_satellites = {}

        for interval in bin_intervals:

            satellite = interval["satellite"]

            norad_id = satellite["norad_id"]

            unique_satellites[norad_id] = satellite

        # Ignore bins with only one satellite
        if len(unique_satellites) < 2:
            continue

        altitude_band, time_bucket = key

        start_time = datetime.fromtimestamp(
            time_bucket * TIME_BUCKET_SECONDS
        )

        end_time = datetime.fromtimestamp(
            (time_bucket + 1) * TIME_BUCKET_SECONDS
        )

        batches.append({
            "satellites": list(
                unique_satellites.values()
            ),

            "altitude_start": altitude_band,

            "altitude_end":
                altitude_band + ALTITUDE_BAND_SIZE_KM,

            "start_time": start_time,

            "end_time": end_time
        })

    print(
        f"Candidate altitude/time batches: "
        f"{len(batches)}"
    )

    return batches
# =========================================================
# 10. EXPERIMENTAL BATCHING PIPELINE
# =========================================================

def prepare_experimental_batches(
    satellites,
    prediction_days=7,
    start_time=None,
    end_time=None
):
    """
    Experimental batching pipeline.

    This contains the new complex batching logic:

        satellites
             ↓
        ONE orbit SGP4
             ↓
        altitude intervals
             ↓
        repeat using orbital period
             ↓
        altitude/time hash
             ↓
        lat/lon for candidates
             ↓
        spatial hash
             ↓
        overlap
             ↓
        batches

    For now this function is ONLY used for testing.
    """

    if not satellites:
        return []

    # -----------------------------------------------------
    # Determine analysis window
    # -----------------------------------------------------

    if start_time is None:
        start_time = min(
            satellite["tle_epoch"]
            for satellite in satellites
        )

    if end_time is None:
        end_time = (
            start_time +
            timedelta(days=prediction_days)
        )

    if end_time <= start_time:
        return []

    print(
        f"Analysis window: "
        f"{start_time} -> {end_time}"
    )

    print(
        f"Processing "
        f"{len(satellites)} satellites..."
    )

    # -----------------------------------------------------
    # STEP 1
    # Learn one-orbit altitude pattern
    # -----------------------------------------------------

    all_one_orbit_intervals = []

    for satellite in satellites:

        one_orbit_intervals = (
            extract_one_orbit_altitude_intervals(
                satellite,
                start_time
            )
        )

        all_one_orbit_intervals.extend(
            one_orbit_intervals
        )

    print(
        f"One-orbit altitude intervals: "
        f"{len(all_one_orbit_intervals)}"
    )

    # -----------------------------------------------------
    # STEP 2
    # Repeat altitude intervals for prediction window
    # -----------------------------------------------------

    all_intervals = []

    intervals_by_satellite = defaultdict(list)

    for interval in all_one_orbit_intervals:

        norad_id = (
            interval["satellite"]
            ["norad_id"]
        )

        intervals_by_satellite[
            norad_id
        ].append(interval)

    for satellite in satellites:

        one_orbit_intervals = (
            intervals_by_satellite.get(
                satellite["norad_id"],
                []
            )
        )

        repeated_intervals = (
            generate_7_day_intervals(
                satellite,
                one_orbit_intervals,
                start_time,
                end_time
            )
        )

        all_intervals.extend(
            repeated_intervals
        )

    print(
        f"Generated "
        f"{len(all_intervals)} "
        f"altitude/time intervals "
        f"for prediction window."
    )

    if not all_intervals:
        return []

    # -----------------------------------------------------
    # STEP 3
    # ALTITUDE + TIME HASH
    # -----------------------------------------------------

    altitude_time_hash = (
        build_altitude_time_hash(
            all_intervals
        )
    )

    candidate_intervals = []
    candidate_ids = set()

    for key, bucket_intervals in (
        altitude_time_hash.items()
    ):

        if len(bucket_intervals) < 2:
            continue

        for interval in bucket_intervals:

            interval_id = id(interval)

            if interval_id not in candidate_ids:

                candidate_ids.add(
                    interval_id
                )

                candidate_intervals.append(
                    interval
                )

    print(
        f"Altitude/time hash reduced "
        f"{len(all_intervals)} intervals "
        f"to {len(candidate_intervals)} "
        f"spatial candidates."
    )

    if not candidate_intervals:
        return []

    # -----------------------------------------------------
    # STEP 4
    # Calculate lat/lon ONLY for candidates
    # -----------------------------------------------------

    spatial_intervals = []

    for interval in candidate_intervals:

        enriched = add_spatial_information(
            interval
        )

        if enriched is not None:

            spatial_intervals.append(
                enriched
            )

    print(
        f"Spatial intervals: "
        f"{len(spatial_intervals)}"
    )

    if not spatial_intervals:
        return []

    # -----------------------------------------------------
    # STEP 5
    # Final spatial batching
    # -----------------------------------------------------

    batches = group_intervals_into_batches(
        spatial_intervals
    )

    # -----------------------------------------------------
    # STEP 6
    # Print batches for testing
    # -----------------------------------------------------

    for index, batch in enumerate(
        batches,
        1
    ):

        norad_ids = [
            satellite["norad_id"]
            for satellite in batch["satellites"]
        ]

        print(
            f"Batch {index}: "
            f"Altitude "
            f"{batch['altitude_start']}-"
            f"{batch['altitude_end']} km, "
            f"Satellites: "
            f"{len(batch['satellites'])}, "
            f"Time: "
            f"{batch['start_time']} -> "
            f"{batch['end_time']}, "
            f"NORAD IDs: "
            f"{norad_ids}"
        )

    print(
        f"Done! Generated "
        f"{len(batches)} batches."
    )

    return batches


# =========================================================
# 11. MAIN FUNCTION
# =========================================================

def prepare_time_filtered_batches(
    satellites,
    prediction_days=7
):
    """
    Main function used by the existing system.

    For now:

        1. Calculate the analysis window
        2. Run experimental batching
        3. Print the batches
        4. Return the ORIGINAL satellites

    This lets us test the batching algorithm without
    changing collision_service yet.
    """

    if not satellites:
        return []

    start_time = min(
        satellite["tle_epoch"]
        for satellite in satellites
    )

    end_time = (
        start_time +
        timedelta(days=prediction_days)
    )

    # Run the experimental batching algorithm.
    # It prints the batches for us to inspect.
    batches = prepare_experimental_batches(
        satellites=satellites,
        prediction_days=prediction_days,
        start_time=start_time,
        end_time=end_time
    )

    # -----------------------------------------------------
    # IMPORTANT:
    # DO NOT return batches yet.
    #
    # collision_service still expects satellites.
    # -----------------------------------------------------

    return [
        {
            "satellites": satellites,
            "altitude_start": None,
            "altitude_end": None,
            "start_time": start_time,
            "end_time": end_time
        }
    ]
