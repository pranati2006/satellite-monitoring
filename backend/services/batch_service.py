from datetime import timedelta
from collections import defaultdict
from math import atan2, degrees, floor, sqrt, sin, cos, pi

from services.sgp4_service import calculate_position

EARTH_RADIUS_KM = 6378.137
ALTITUDE_BAND_SIZE_KM = 100
GRID_CELL_SIZE_DEG = 5.0
PROPAGATION_STEP_SECONDS = 30  # Step interval for trajectory sampling


# ---------------------------------------------------------
# 1. Physics & Coordinate Helpers
# ---------------------------------------------------------

def calculate_altitude(position):
    x, y, z = float(position["x"]), float(position["y"]), float(position["z"])
    return sqrt(x * x + y * y + z * z) - EARTH_RADIUS_KM


def calculate_latitude_longitude(position, timestamp):
    x, y, z = float(position["x"]), float(position["y"]), float(position["z"])
    seconds_since_epoch = timestamp.timestamp()
    earth_rotation_angle = (seconds_since_epoch * 7.2921159e-5) % (2 * pi)

    cos_angle, sin_angle = cos(earth_rotation_angle), sin(earth_rotation_angle)
    x_ecef = cos_angle * x + sin_angle * y
    y_ecef = -sin_angle * x + cos_angle * y

    longitude = degrees(atan2(y_ecef, x_ecef))
    latitude = degrees(atan2(z, sqrt(x_ecef * x_ecef + y_ecef * y_ecef)))

    return {"latitude": latitude, "longitude": longitude}


def get_position_and_altitude(satellite, timestamp):
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
    except ValueError:
        return None

    if result is None:
        return None

    position = result["position_km"]
    altitude = calculate_altitude(position)
    lat_lon = calculate_latitude_longitude(position, timestamp)

    return {
        "timestamp": timestamp,
        "altitude": altitude,
        "latitude": lat_lon["latitude"],
        "longitude": lat_lon["longitude"]
    }


def get_altitude_band_key(altitude):
    return floor(altitude / ALTITUDE_BAND_SIZE_KM) * ALTITUDE_BAND_SIZE_KM


# ---------------------------------------------------------
# 2. Bounding Square Creation
# ---------------------------------------------------------

def create_square(points):
    min_lat = min(pt["latitude"] for pt in points)
    max_lat = max(pt["latitude"] for pt in points)
    lons = [pt["longitude"] for pt in points]

    if max_lat > 80.0 or min_lat < -80.0:
        return {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": -180.0,
            "max_lon": 180.0,
            "crosses_antimeridian": False
        }

    # Detect anti-meridian wrap-around
    crosses_antimeridian = any(abs(lons[i] - lons[i - 1]) > 180.0 for i in range(1, len(lons)))

    if crosses_antimeridian:
        neg_lons = [l for l in lons if l < 0]
        pos_lons = [l for l in lons if l >= 0]
        min_lon = max(neg_lons) if neg_lons else -180.0
        max_lon = min(pos_lons) if pos_lons else 180.0
    else:
        min_lon = min(lons)
        max_lon = max(lons)

    return {
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lon": min_lon,
        "max_lon": max_lon,
        "crosses_antimeridian": crosses_antimeridian
    }


# ---------------------------------------------------------
# 3. Satellite-First Trajectory & Segment Extraction
# ---------------------------------------------------------

def extract_satellite_altitude_intervals(satellite, start_time):
    """
    Runs ONE satellite through its trajectory (1 revolution) 
    and slices its path into altitude-band intervals with bounding squares.
    """
    mean_motion = satellite["mean_motion"]
    orbital_period_seconds = int(86400 / mean_motion)
    end_time = start_time + timedelta(seconds=orbital_period_seconds)

    intervals = []
    current_time = start_time
    current_band = None
    current_points = []

    while current_time <= end_time:
        point = get_position_and_altitude(satellite, current_time)
        if point is not None:
            band = get_altitude_band_key(point["altitude"])

            if current_band is None:
                current_band = band
                current_points = [point]
            elif band == current_band:
                current_points.append(point)
            else:
                # Satellite moved to a new altitude band -> seal previous interval
                if len(current_points) >= 2:
                    intervals.append({
                        "satellite": satellite,
                        "altitude_start": current_band,
                        "altitude_end": current_band + ALTITUDE_BAND_SIZE_KM,
                        "start_time": current_points[0]["timestamp"],
                        "end_time": current_points[-1]["timestamp"],
                        "square": create_square(current_points)
                    })
                current_band = band
                current_points = [point]

        current_time += timedelta(seconds=PROPAGATION_STEP_SECONDS)

    # Flush final segment
    if len(current_points) >= 2:
        intervals.append({
            "satellite": satellite,
            "altitude_start": current_band,
            "altitude_end": current_band + ALTITUDE_BAND_SIZE_KM,
            "start_time": current_points[0]["timestamp"],
            "end_time": current_points[-1]["timestamp"],
            "square": create_square(current_points)
        })

    return intervals


# ---------------------------------------------------------
# 4. Spatial Hashing & Overlap Grouping
# ---------------------------------------------------------

def get_grid_cells(square):
    min_lat_cell = floor(square["min_lat"] / GRID_CELL_SIZE_DEG)
    max_lat_cell = floor(square["max_lat"] / GRID_CELL_SIZE_DEG)
    min_lon_cell = floor(square["min_lon"] / GRID_CELL_SIZE_DEG)
    max_lon_cell = floor(square["max_lon"] / GRID_CELL_SIZE_DEG)

    cells = []
    if not square.get("crosses_antimeridian", False):
        for lat_cell in range(min_lat_cell, max_lat_cell + 1):
            for lon_cell in range(min_lon_cell, max_lon_cell + 1):
                cells.append((lat_cell, lon_cell))
    else:
        max_lon_bin = floor(180.0 / GRID_CELL_SIZE_DEG) - 1
        min_lon_bin = floor(-180.0 / GRID_CELL_SIZE_DEG)
        lon_ranges = [
            range(min_lon_cell, max_lon_bin + 1),
            range(min_lon_bin, max_lon_cell + 1)
        ]
        for lat_cell in range(min_lat_cell, max_lat_cell + 1):
            for lon_range in lon_ranges:
                for lon_cell in lon_range:
                    cells.append((lat_cell, lon_cell))

    return cells


def intervals_overlap(inv1, inv2):
    # Time overlap check
    if inv1["end_time"] < inv2["start_time"] or inv2["end_time"] < inv1["start_time"]:
        return False

    # Spatial bounding box overlap check
    sq1, sq2 = inv1["square"], inv2["square"]
    if sq1["max_lat"] < sq2["min_lat"] or sq2["max_lat"] < sq1["min_lat"]:
        return False

    if not sq1.get("crosses_antimeridian") and not sq2.get("crosses_antimeridian"):
        if sq1["max_lon"] < sq2["min_lon"] or sq2["max_lon"] < sq1["min_lon"]:
            return False
        return True

    return True


def group_intervals_into_batches(intervals):
    """
    Groups intervals sharing the same altitude band, overlapping time, and spatial grid cells.
    """
    # Key by altitude band key (e.g., 500 -> 500-600km)
    band_groups = defaultdict(list)
    for inv in intervals:
        band_groups[inv["altitude_start"]].append(inv)

    all_batches = []

    for altitude_start, band_intervals in band_groups.items():
        if len(band_intervals) < 2:
            continue

        grid = defaultdict(list)
        for inv in band_intervals:
            for cell in get_grid_cells(inv["square"]):
                grid[cell].append(inv)

        visited = set()

        for inv in band_intervals:
            inv_id = (inv["satellite"]["norad_id"], inv["start_time"])
            if inv_id in visited:
                continue

            cluster = []
            stack = [inv]

            while stack:
                current = stack.pop()
                curr_id = (current["satellite"]["norad_id"], current["start_time"])

                if curr_id in visited:
                    continue

                visited.add(curr_id)
                cluster.append(current)

                for cell in get_grid_cells(current["square"]):
                    for candidate in grid.get(cell, []):
                        cand_id = (candidate["satellite"]["norad_id"], candidate["start_time"])
                        if cand_id not in visited and intervals_overlap(current, candidate):
                            stack.append(candidate)

            if len(cluster) >= 2:
                # Aggregate clustered intervals into a batch output
                unique_sats = list({inv["satellite"]["norad_id"]: inv["satellite"] for inv in cluster}.values())
                all_batches.append({
                    "satellites": unique_sats,
                    "altitude_start": altitude_start,
                    "altitude_end": altitude_start + ALTITUDE_BAND_SIZE_KM,
                    "start_time": min(inv["start_time"] for inv in cluster),
                    "end_time": max(inv["end_time"] for inv in cluster)
                })

    return all_batches


# ---------------------------------------------------------
# 5. Main Execution Entry Point
# ---------------------------------------------------------

def prepare_experimental_batches(satellites, prediction_days=7):
    if not satellites:
        return []

    start_time = min(satellite["tle_epoch"] for satellite in satellites)

    # 1. Run each satellite ONCE over its trajectory and collect intervals
    all_intervals = []
    print(f"Processing {len(satellites)} satellites individually...")
    for satellite in satellites:
        intervals = extract_satellite_altitude_intervals(satellite, start_time)
        all_intervals.extend(intervals)

    # 2. Group intervals into spatial/temporal batches
    batches = group_intervals_into_batches(all_intervals)
    for i, batch in enumerate(batches, 1):
        norad_ids = [sat["norad_id"] for sat in batch["satellites"]]

        print(
            f"Batch {i}: "
            f"Altitude {batch['altitude_start']}-{batch['altitude_end']} km, "
            f"Satellites: {len(batch['satellites'])}, "
            f"NORAD IDs: {norad_ids}"
        )

    print(f"Done! Generated {len(batches)} batches from {len(all_intervals)} total path segments.")
    return batches


def prepare_time_filtered_batches(satellites, prediction_days=7):
    if not satellites:
        return []

    start_time = min(satellite["tle_epoch"] for satellite in satellites)
    end_time = start_time + timedelta(days=prediction_days)

    prepare_experimental_batches(satellites, prediction_days=prediction_days)

    return [{
        "satellites": satellites,
        "altitude_start": None,
        "altitude_end": None,
        "start_time": start_time,
        "end_time": end_time
    }]