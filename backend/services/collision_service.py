from datetime import timedelta
from services.sgp4_service import calculate_position
from config import (
    SCREENING_EPS_KM,
    SCREENING_INTERVAL_MINUTES,
    PREDICTION_DAYS
)
from services.grid_service import find_grid_candidates
from services.batch_service import prepare_time_filtered_batches
import math
EARTH_RADIUS_KM = 6378.137
MU_EARTH = 398600.4418



def calculate_distance(position1, position2):

    dx = position1["x"] - position2["x"]
    dy = position1["y"] - position2["y"]
    dz = position1["z"] - position2["z"]

    return (dx**2 + dy**2 + dz**2) ** 0.5


def detailed_analysis(sat1, sat2, timestamp):

    # Analyze 1 minute before and after
    start_time = timestamp - timedelta(minutes=SCREENING_INTERVAL_MINUTES)
    end_time = timestamp + timedelta(minutes=SCREENING_INTERVAL_MINUTES)

    current_time = start_time

    min_distance = float("inf")
    min_time = None

    while current_time <= end_time:

        # SGP4 propagation at CURRENT time
        result1 = calculate_position(
            sat1.tle_line1,
            sat1.tle_line2,
            current_time.year,
            current_time.month,
            current_time.day,
            current_time.hour,
            current_time.minute,
            current_time.second
        )

        result2 = calculate_position(
            sat2.tle_line1,
            sat2.tle_line2,
            current_time.year,
            current_time.month,
            current_time.day,
            current_time.hour,
            current_time.minute,
            current_time.second
        )

        # Get positions from result
        position1 = result1["position_km"]
        position2 = result2["position_km"]

        # Calculate distance
        distance = calculate_distance(
            position1,
            position2
        )

        # Track minimum
        if distance < min_distance:
            min_distance = distance
            min_time = current_time

        current_time += timedelta(seconds=1)

    return {
        "tca": min_time,
        "minimum_distance_km": min_distance
    }

#collsiion screen through grid

def screen_satellites(
    satellites,
    eps_km=SCREENING_EPS_KM
):
    """
    Complete conjunction screening pipeline.

    1. Create altitude batches
    2. Calculate altitude entry/exit intervals
    3. Find common time windows
    4. Run SGP4 only inside those windows
    5. Run spatial grid
    6. Return candidate pairs
    """

    # --------------------------------------------------------
    # STEP 1:
    # Create altitude + time filtered batches
    # --------------------------------------------------------

    batches = prepare_time_filtered_batches(
        satellites,
        prediction_days=PREDICTION_DAYS
    )


    all_candidates = {}

    # --------------------------------------------------------
    # STEP 2:
    # Process each batch
    # --------------------------------------------------------

    for batch_info in batches:

        batch = batch_info["satellites"]

        start_time = batch_info["start_time"]

        end_time = batch_info["end_time"]

        altitude_start = (
            batch_info["altitude_start"]
        )

        altitude_end = (
            batch_info["altitude_end"]
        )

        print(
            f"\nScreening batch:"
            f"\n  Satellites: {len(batch)}"
            f"\n  Altitude: "
            f"{altitude_start}-"
            f"{altitude_end} km"
            f"\n  Start: {start_time}"
            f"\n  End: {end_time}"
        )

        # ----------------------------------------------------
        # STEP 3:
        # SGP4 + Grid ONLY inside this window
        # ----------------------------------------------------

        candidates = screen_batch(
            batch,
            start_time,
            end_time,
            eps_km
        )

        # ----------------------------------------------------
        # STEP 4:
        # Merge candidates from all batches
        # ----------------------------------------------------

        for key, candidate in candidates.items():

            if (
                key not in all_candidates
                or
                candidate["distance_km"]
                <
                all_candidates[key]["distance_km"]
            ):

                all_candidates[key] = candidate

    # --------------------------------------------------------
    # STEP 5:
    # Return all unique candidate pairs
    # --------------------------------------------------------

    return list(
        all_candidates.values()
    )

#batch making:

def screen_batch(
    batch,
    start_time,
    end_time,
    eps_km
):
    """
    Runs SGP4 + spatial grid for ONE
    time-filtered batch.

    SGP4 is only performed between
    start_time and end_time.
    """

    candidate_pairs = {}

    current_time = start_time

    while current_time <= end_time:

        # ----------------------------------------------------
        # 1. Propagate satellites using SGP4
        # ----------------------------------------------------

        available_satellites = []

        for satellite in batch:

            try:
                result = calculate_position(
                    satellite["tle_line1"],
                    satellite["tle_line2"],
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    current_time.hour,
                    current_time.minute,
                    current_time.second
                )
            except ValueError as e:
                continue

            if result is None:
                continue

            available_satellites.append({
                "id": satellite["id"],
                "norad_id": satellite["norad_id"],
                "position": result["position_km"],
                "velocity": result["velocity_km_s"]
            })

        # ----------------------------------------------------
        # 2. Need at least two satellites
        # ----------------------------------------------------

        if len(available_satellites) >= 2:
            pairs = find_grid_candidates(
                available_satellites,
                eps_km
            )

            # ------------------------------------------------
            # 4. Fast lookup by satellite ID
            # ------------------------------------------------

            satellite_by_id = {
                satellite["id"]: satellite
                for satellite in available_satellites
            }

            # ------------------------------------------------
            # 5. Exact distance check
            # ------------------------------------------------

            for id1, id2 in pairs:

                sat1 = satellite_by_id[id1]
                sat2 = satellite_by_id[id2]

                distance = calculate_distance(
                    sat1["position"],
                    sat2["position"]
                )

                # Grid gives possible candidates.
                # Now verify actual distance.

                if distance > eps_km:
                    continue

                key = (
                    min(id1, id2),
                    max(id1, id2)
                )

                if (
                    key not in candidate_pairs
                    or
                    distance
                    <
                    candidate_pairs[key]["distance_km"]
                ):

                    candidate_pairs[key] = {

                        "satellite_1_id":
                            sat1["id"],

                        "satellite_2_id":
                            sat2["id"],

                        "satellite_1_norad_id":
                            sat1["norad_id"],

                        "satellite_2_norad_id":
                            sat2["norad_id"],

                        "time":
                            current_time,

                        "distance_km":
                            distance
                    }

        # ----------------------------------------------------
        # 6. Next screening time
        # ----------------------------------------------------

        current_time += timedelta(
            minutes=SCREENING_INTERVAL_MINUTES
        )

    return candidate_pairs