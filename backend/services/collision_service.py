from datetime import timedelta
from itertools import combinations

from services.dbscan_service import find_clusters
from services.sgp4_service import calculate_position
from config import (
    SCREENING_EPS_KM,
    SCREENING_INTERVAL_MINUTES,
    PREDICTION_DAYS
)
from collections import defaultdict
from itertools import combinations
import math



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
        # if len(available_satellites) >= 2:

        #     clusters = find_clusters(
        #         available_satellites,
        #         eps_km=eps_km,
        #         min_samples=2
        #     )

        #     # 3. Generate pairs inside each cluster
        #     for cluster in clusters:

        #         for sat1, sat2 in combinations(cluster, 2):

        #             distance = calculate_distance(
        #                 sat1["position"],
        #                 sat2["position"]
        #             )

        #             pair = tuple(sorted(
        #                    [sat1, sat2],
        #                    key=lambda x: x["id"]
        #             )) 
        #             pair_key = (
        #                        pair[0]["id"],
        #                        pair[1]["id"]
        #             )                       

        #             # 4. First occurrence
        #             if pair_key not in closest_pairs:

        #                 closest_pairs[pair_key] = {
        #                             "satellite_1_id": pair[0]["id"],
        #                             "satellite_2_id": pair[1]["id"],
        #                             "satellite_1_norad_id": pair[0]["norad_id"],
        #                             "satellite_2_norad_id": pair[1]["norad_id"],
        #                             "time": timestamp,
        #                             "distance_km": distance
        #                         }
        #             # 5. Replace if this timestamp is closer
        #             elif distance < closest_pairs[pair_key]["distance_km"]:

        #                 closest_pairs[pair_key] = {
        #                     "satellite_1_id": pair[0]["id"],
        #                     "satellite_2_id": pair[1]["id"],
        #                     "satellite_1_norad_id": pair[0]["norad_id"],
        #                     "satellite_2_norad_id": pair[1]["norad_id"],
        #                     "time": timestamp,
        #                     "distance_km": distance
        #                 }
        # 2. Hash-based spatial grid
        if len(available_satellites) >= 2:

            candidate_pairs = find_grid_candidates(available_satellites,eps_km=eps_km)

           # Create quick lookup by satellite ID
            satellite_lookup = {satellite["id"]: satellite for satellite in available_satellites}

           # 3. Check exact distance only for candidates
            for id1, id2 in candidate_pairs:

                sat1 = satellite_lookup[id1]
                sat2 = satellite_lookup[id2]

                distance = calculate_distance(
                    sat1["position"],
                    sat2["position"]
                )

                if distance <= eps_km:

                    pair = tuple(sorted(
                        [sat1, sat2],
                        key=lambda x: x["id"]
                    ))

                    pair_key = (
                        pair[0]["id"],
                        pair[1]["id"]
                    )

                    if pair_key not in closest_pairs:

                        closest_pairs[pair_key] = {
                            "satellite_1_id": pair[0]["id"],
                            "satellite_2_id": pair[1]["id"],
                            "satellite_1_norad_id": pair[0]["norad_id"],
                            "satellite_2_norad_id": pair[1]["norad_id"],
                            "time": timestamp,
                            "distance_km": distance
                        }

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



#collsiion screen through grid



def find_grid_candidates(satellites, eps_km):
    """
    Find satellite pairs that are within eps_km
    using a hash-based 3D spatial grid.
    """

    cell_size = eps_km

    grid = defaultdict(list)

    # ------------------------------------------------
    # 1. Put every satellite into a grid cell
    # ------------------------------------------------

    for satellite in satellites:

        x = float(satellite["position"]["x"])
        y = float(satellite["position"]["y"])
        z = float(satellite["position"]["z"])   

        cell = (
            math.floor(x / cell_size),
            math.floor(y / cell_size),
            math.floor(z / cell_size)
        )

        grid[cell].append(satellite)

    # ------------------------------------------------
    # 2. Check this cell + neighboring cells
    # ------------------------------------------------

    candidate_pairs = set()

    for cell, cell_satellites in grid.items():

        cx, cy, cz = cell

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):

                    neighbor_cell = (
                        cx + dx,
                        cy + dy,
                        cz + dz
                    )

                    if neighbor_cell not in grid:
                        continue

                    for sat1 in cell_satellites:
                        for sat2 in grid[neighbor_cell]:

                            if sat1["id"] == sat2["id"]:
                                continue

                            pair_key = tuple(sorted(
                                [sat1["id"], sat2["id"]]
                            ))

                            candidate_pairs.add(pair_key)

    return candidate_pairs