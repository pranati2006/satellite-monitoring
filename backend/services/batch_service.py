from datetime import datetime, timedelta
from collections import defaultdict
from math import atan2, degrees, floor, sqrt, sin, cos, pi

from services.sgp4_service import calculate_position


# =========================================================
# CONFIGURATION
# =========================================================

EARTH_RADIUS_KM = 6378.137

ALTITUDE_BAND_SIZE_KM = 100

TIME_BUCKET_SECONDS = 300  # 5 minutes

GRID_CELL_SIZE_DEG = 5.0

PROPAGATION_STEP_SECONDS = 30


# =========================================================
# 1. PHYSICS / COORDINATE HELPERS
# =========================================================

def calculate_altitude(position):

    x = float(position["x"])
    y = float(position["y"])
    z = float(position["z"])

    radius = sqrt(x * x + y * y + z * z)

    return radius - EARTH_RADIUS_KM


def calculate_latitude_longitude(position, timestamp):

    x = float(position["x"])
    y = float(position["y"])
    z = float(position["z"])

    seconds_since_epoch = timestamp.timestamp()

    earth_rotation_angle = (
        seconds_since_epoch * 7.2921159e-5
    ) % (2 * pi)

    cos_angle = cos(earth_rotation_angle)
    sin_angle = sin(earth_rotation_angle)

    x_ecef = (
        cos_angle * x +
        sin_angle * y
    )

    y_ecef = (
        -sin_angle * x +
        cos_angle * y
    )

    longitude = degrees(
        atan2(
            y_ecef,
            x_ecef
        )
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


def get_position_and_altitude(
    satellite,
    timestamp
):

    position = get_position(
        satellite,
        timestamp
    )

    if position is None:

        return None

    altitude = calculate_altitude(
        position
    )

    return {
        "timestamp": timestamp,
        "altitude": altitude,
        "position": position
    }


def get_altitude_band_key(altitude):

    return (
        floor(
            altitude /
            ALTITUDE_BAND_SIZE_KM
        )
        * ALTITUDE_BAND_SIZE_KM
    )


def get_orbital_period_seconds(satellite):

    mean_motion = float(
        satellite["mean_motion"]
    )

    if mean_motion <= 0:

        return None

    return 86400.0 / mean_motion


# =========================================================
# 2. SPATIAL GRID HELPERS
# =========================================================

def get_lat_lon_cell(
    latitude,
    longitude
):

    lat_cell = floor(
        latitude /
        GRID_CELL_SIZE_DEG
    )

    lon_cell = floor(
        longitude /
        GRID_CELL_SIZE_DEG
    )

    return (
        lat_cell,
        lon_cell
    )


def get_neighbor_cells(
    lat_cell,
    lon_cell
):

    cells = []

    for dlat in (-1, 0, 1):

        for dlon in (-1, 0, 1):

            cells.append(
                (
                    lat_cell + dlat,
                    lon_cell + dlon
                )
            )

    return cells


# =========================================================
# 3. LEARN ONE ORBITAL REVOLUTION
# =========================================================

def extract_one_orbit_altitude_intervals(
    satellite,
    start_time
):

    period_seconds = (
        get_orbital_period_seconds(
            satellite
        )
    )

    if period_seconds is None:

        return []

    end_time = (
        start_time +
        timedelta(
            seconds=period_seconds
        )
    )

    intervals = []

    current_time = start_time

    current_band = None
    current_start_time = None

    spatial_cells = set()

    while current_time <= end_time:

        point = get_position_and_altitude(
            satellite,
            current_time
        )

        if point is not None:

            band = get_altitude_band_key(
                point["altitude"]
            )

            lat_lon = (
                calculate_latitude_longitude(
                    point["position"],
                    point["timestamp"]
                )
            )

            lat_cell, lon_cell = (
                get_lat_lon_cell(
                    lat_lon["latitude"],
                    lat_lon["longitude"]
                )
            )

            # -----------------------------------------
            # First point
            # -----------------------------------------

            if current_band is None:

                current_band = band

                current_start_time = (
                    point["timestamp"]
                )

                spatial_cells = set()

                spatial_cells.add(
                    (
                        lat_cell,
                        lon_cell
                    )
                )

            # -----------------------------------------
            # Same altitude band
            # -----------------------------------------

            elif band == current_band:

                spatial_cells.add(
                    (
                        lat_cell,
                        lon_cell
                    )
                )

            # -----------------------------------------
            # Altitude band changed
            # -----------------------------------------

            else:

                if current_start_time is not None:

                    intervals.append({

                        "satellite":
                            satellite,

                        "altitude_start":
                            current_band,

                        "altitude_end":
                            (
                                current_band +
                                ALTITUDE_BAND_SIZE_KM
                            ),

                        "start_offset":
                            (
                                current_start_time -
                                start_time
                            ),

                        "end_offset":
                            (
                                point["timestamp"] -
                                start_time
                            ),

                        "spatial_cells":
                            spatial_cells
                    })

                current_band = band

                current_start_time = (
                    point["timestamp"]
                )

                spatial_cells = set()

                spatial_cells.add(
                    (
                        lat_cell,
                        lon_cell
                    )
                )

        current_time += timedelta(
            seconds=PROPAGATION_STEP_SECONDS
        )

    # -----------------------------------------
    # Flush final interval
    # -----------------------------------------

    if (
        current_band is not None
        and current_start_time is not None
    ):

        intervals.append({

            "satellite":
                satellite,

            "altitude_start":
                current_band,

            "altitude_end":
                (
                    current_band +
                    ALTITUDE_BAND_SIZE_KM
                ),

            "start_offset":
                (
                    current_start_time -
                    start_time
                ),

            "end_offset":
                (
                    end_time -
                    start_time
                ),

            "spatial_cells":
                spatial_cells
        })

    return intervals


# =========================================================
# 4. REPEAT INTERVALS FOR PREDICTION WINDOW
# =========================================================

def generate_7_day_intervals(
    satellite,
    one_orbit_intervals,
    start_time,
    end_time
):

    period_seconds = (
        get_orbital_period_seconds(
            satellite
        )
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

            if interval_end < start_time:

                continue

            if interval_start > end_time:

                continue

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
                        clipped_end,

                    "spatial_cells":
                        interval[
                            "spatial_cells"
                        ]
                })

        revolution_start += period

    return generated


# =========================================================
# 5. TIME HASH
# =========================================================

def get_time_bucket(timestamp):

    unix_seconds = int(
        timestamp.timestamp()
    )

    return (
        unix_seconds //
        TIME_BUCKET_SECONDS
    )


def build_altitude_time_hash(intervals):

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

        for bucket in range(
            start_bucket,
            end_bucket + 1
        ):

            interval_hash[
                (
                    altitude_band,
                    bucket
                )
            ].append(
                interval
            )

    return interval_hash


# =========================================================
# 6. ALTITUDE + TIME + SPATIAL HASH
# =========================================================

def build_altitude_time_spatial_hash(
    intervals
):

    spatial_hash = defaultdict(set)

    for interval in intervals:

        altitude_band = (
            interval["altitude_start"]
        )

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

            for lat_cell, lon_cell in (
                interval["spatial_cells"]
            ):

                key = (
                    altitude_band,
                    time_bucket,
                    lat_cell,
                    lon_cell
                )

                spatial_hash[key].add(
                    interval[
                        "satellite"
                    ]["norad_id"]
                )

    return spatial_hash


# =========================================================
# 7. FINAL BATCHING
# =========================================================

# =========================================================
# 7. FINAL BATCHING
# =========================================================

def group_intervals_into_batches(intervals):

    spatial_hash = (
        build_altitude_time_spatial_hash(
            intervals
        )
    )

    print(
        f"Total altitude/time/spatial bins: "
        f"{len(spatial_hash)}"
    )

    satellites_by_id = {}

    for interval in intervals:

        satellite = interval["satellite"]

        norad_id = satellite["norad_id"]

        satellites_by_id[norad_id] = satellite

    # -----------------------------------------------------
    # Group spatial cells by altitude + time
    # -----------------------------------------------------

    altitude_time_cells = defaultdict(list)

    for key, satellite_ids in spatial_hash.items():

        if len(satellite_ids) < 2:
            continue

        altitude_band, time_bucket, lat_cell, lon_cell = key

        altitude_time_cells[
            (altitude_band, time_bucket)
        ].append(
            satellite_ids
        )

    batches = []

    # -----------------------------------------------------
    # Process every altitude + time band
    # -----------------------------------------------------

    for (
        altitude_band,
        time_bucket
    ), spatial_groups in altitude_time_cells.items():

        # -------------------------------------------------
        # We don't compare groups with each other.
        #
        # Instead, build connected groups using a
        # satellite -> group mapping.
        # -------------------------------------------------

        groups = []

        satellite_to_group = {}

        for satellite_ids in spatial_groups:

            current_group_ids = set()

            existing_group_indexes = set()

            # ---------------------------------------------
            # Find groups already containing these satellites
            #
            # This uses a dictionary lookup instead of
            # comparing this group with every other group.
            # ---------------------------------------------

            for norad_id in satellite_ids:

                group_index = satellite_to_group.get(
                    norad_id
                )

                if group_index is not None:

                    existing_group_indexes.add(
                        group_index
                    )

            # ---------------------------------------------
            # No existing group
            # ---------------------------------------------

            if not existing_group_indexes:

                new_group = set(
                    satellite_ids
                )

                groups.append(
                    new_group
                )

                new_group_index = len(groups) - 1

                for norad_id in new_group:

                    satellite_to_group[
                        norad_id
                    ] = new_group_index

                continue

            # ---------------------------------------------
            # Merge into the existing group
            # ---------------------------------------------

            main_group_index = min(
                existing_group_indexes
            )

            main_group = groups[
                main_group_index
            ]

            main_group.update(
                satellite_ids
            )

            # ---------------------------------------------
            # If this spatial cell connects multiple
            # existing groups, merge those groups.
            # ---------------------------------------------

            for group_index in sorted(
                existing_group_indexes
            ):

                if group_index == main_group_index:

                    continue

                other_group = groups[
                    group_index
                ]

                main_group.update(
                    other_group
                )

                groups[
                    group_index
                ] = set()

                for norad_id in other_group:

                    satellite_to_group[
                        norad_id
                    ] = main_group_index

            # ---------------------------------------------
            # Update mapping for all satellites
            # ---------------------------------------------

            for norad_id in main_group:

                satellite_to_group[
                    norad_id
                ] = main_group_index

        # -------------------------------------------------
        # Create final batches
        # -------------------------------------------------

        start_time = datetime.fromtimestamp(
            time_bucket *
            TIME_BUCKET_SECONDS
        )

        end_time = datetime.fromtimestamp(
            (
                time_bucket + 1
            ) *
            TIME_BUCKET_SECONDS
        )

        for group in groups:

            if len(group) < 2:

                continue

            unique_satellites = [

                satellites_by_id[norad_id]

                for norad_id in group

                if norad_id in satellites_by_id
            ]

            if len(unique_satellites) < 2:

                continue

            batches.append({

                "satellites":
                    unique_satellites,

                "altitude_start":
                    altitude_band,

                "altitude_end":
                    (
                        altitude_band +
                        ALTITUDE_BAND_SIZE_KM
                    ),

                "start_time":
                    start_time,

                "end_time":
                    end_time
            })

    print(
        f"Spatially filtered candidate batches: "
        f"{len(batches)}"
    )

    return batches
# =========================================================
# 8. EXPERIMENTAL BATCHING PIPELINE
# =========================================================

def prepare_experimental_batches(
    satellites,
    prediction_days=7,
    start_time=None,
    end_time=None
):

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
            timedelta(
                days=prediction_days
            )
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
    # Learn one orbit
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
    # Repeat for 7 days
    # -----------------------------------------------------

    all_intervals = []

    intervals_by_satellite = defaultdict(
        list
    )

    for interval in (
        all_one_orbit_intervals
    ):

        norad_id = (
            interval[
                "satellite"
            ]["norad_id"]
        )

        intervals_by_satellite[
            norad_id
        ].append(
            interval
        )

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
        f"altitude/time/spatial intervals "
        f"for prediction window."
    )

    if not all_intervals:

        return []

    # -----------------------------------------------------
    # STEP 3
    # Altitude + time filtering
    # -----------------------------------------------------

    altitude_time_hash = (
        build_altitude_time_hash(
            all_intervals
        )
    )

    candidate_intervals = []

    candidate_ids = set()

    for (
        key,
        bucket_intervals
    ) in altitude_time_hash.items():

        if len(bucket_intervals) < 2:

            continue

        for interval in bucket_intervals:

            interval_id = id(
                interval
            )

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
    # Spatial hashing + batching
    #
    # NO extra SGP4 here.
    # -----------------------------------------------------

    batches = (
        group_intervals_into_batches(
            candidate_intervals
        )
    )

    # -----------------------------------------------------
    # STEP 5
    # Print batches
    # -----------------------------------------------------

    for index, batch in enumerate(
        batches,
        1
    ):

        norad_ids = [

            satellite["norad_id"]

            for satellite
            in batch["satellites"]
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
# 9. MAIN FUNCTION
# =========================================================

def prepare_time_filtered_batches(
    satellites,
    prediction_days=7
):

    if not satellites:

        return []

    start_time = min(
        satellite["tle_epoch"]
        for satellite in satellites
    )

    end_time = (
        start_time +
        timedelta(
            days=prediction_days
        )
    )

    # Run experimental batching.
    prepare_experimental_batches(
        satellites=satellites,
        prediction_days=prediction_days,
        start_time=start_time,
        end_time=end_time
    )

    # IMPORTANT:
    # collision_service still expects the
    # original batch structure.

    return [
        {
            "satellites": satellites,

            "altitude_start": None,

            "altitude_end": None,

            "start_time": start_time,

            "end_time": end_time
        }
    ]