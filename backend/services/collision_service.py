from datetime import timedelta
from itertools import combinations

from services.dbscan_service import find_clusters
from services.sgp4_service import calculate_position
from config import (
    SCREENING_EPS_KM,
    SCREENING_INTERVAL_MINUTES,
    PREDICTION_DAYS
)


def calculate_distance(position1, position2):

    dx = position1["x"] - position2["x"]
    dy = position1["y"] - position2["y"]
    dz = position1["z"] - position2["z"]

    return (dx**2 + dy**2 + dz**2) ** 0.5


def screen_satellites(
    satellites,
    current_time,
    end_time,
    eps_km
):

    closest_pairs = {}

    timestamp = current_time

    while timestamp <= end_time:

        available_satellites = []

        # 1. Find satellites valid at this timestamp
        for satellite in satellites:

            satellite_end = (
                satellite["tle_epoch"]
                + timedelta(days=PREDICTION_DAYS)
            )

            if (
                timestamp >= satellite["tle_epoch"]
                and timestamp <= satellite_end
            ):

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

                available_satellites.append({
                    "id": satellite["id"],
                    "norad_id": satellite["norad_id"],
                    "position": result["position_km"],
                    "velocity": result["velocity_km_s"]
                })

        # 2. DBSCAN for this timestamp
        if len(available_satellites) >= 2:

            clusters = find_clusters(
                available_satellites,
                eps_km=eps_km,
                min_samples=2
            )

            # 3. Generate pairs inside each cluster
            for cluster in clusters:

                for sat1, sat2 in combinations(cluster, 2):

                    distance = calculate_distance(
                        sat1["position"],
                        sat2["position"]
                    )

                    pair = tuple(sorted(
                           [sat1, sat2],
                           key=lambda x: x["id"]
                    )) 
                    pair_key = (
                               pair[0]["id"],
                               pair[1]["id"]
                    )                       

                    # 4. First occurrence
                    if pair_key not in closest_pairs:

                        closest_pairs[pair_key] = {
                                    "satellite_1_id": pair[0]["id"],
                                    "satellite_2_id": pair[1]["id"],
                                    "satellite_1_norad_id": pair[0]["norad_id"],
                                    "satellite_2_norad_id": pair[1]["norad_id"],
                                    "time": timestamp,
                                    "distance_km": distance
                                }
                    # 5. Replace if this timestamp is closer
                    elif distance < closest_pairs[pair_key]["distance_km"]:

                        closest_pairs[pair_key] = {
                            "satellite_1_id": pair[0]["id"],
                            "satellite_2_id": pair[1]["id"],
                            "satellite_1_norad_id": pair[0]["norad_id"],
                            "satellite_2_norad_id": pair[1]["norad_id"],
                            "time": timestamp,
                            "distance_km": distance
                        }

        timestamp += timedelta(minutes=SCREENING_INTERVAL_MINUTES)

    return list(closest_pairs.values())

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