# services/grid_service.py

import math
from collections import defaultdict


def find_grid_candidates(satellites, eps_km):
    """
    Finds possible nearby satellite pairs using
    a 3D spatial grid.

    satellites:
        [
            {
                "id": ...,
                "norad_id": ...,
                "position": {
                    "x": ...,
                    "y": ...,
                    "z": ...
                }
            },
            ...
        ]

    eps_km:
        Maximum distance threshold in km.

    Returns:
        Set of candidate pairs:

        {
            (satellite_id_1, satellite_id_2),
            ...
        }
    """

    # Cell size is the distance threshold
    cell_size = eps_km

    # --------------------------------------------------------
    # 1. Put every satellite into a grid cell
    # --------------------------------------------------------

    grid = defaultdict(list)

    for satellite in satellites:

        position = satellite["position"]

        x = float(position["x"])
        y = float(position["y"])
        z = float(position["z"])

        cell = (
            math.floor(x / cell_size),
            math.floor(y / cell_size),
            math.floor(z / cell_size)
        )

        grid[cell].append(satellite)

    # --------------------------------------------------------
    # 2. Check neighboring cells
    # --------------------------------------------------------

    candidate_pairs = set()

    for cell, cell_satellites in grid.items():

        cx, cy, cz = cell

        # Check current cell + 26 neighboring cells
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

                    neighbor_satellites = grid[
                        neighbor_cell
                    ]

                    # ------------------------------------------------
                    # Compare satellites between the two cells
                    # ------------------------------------------------

                    for sat1 in cell_satellites:

                        for sat2 in neighbor_satellites:

                            id1 = sat1["id"]
                            id2 = sat2["id"]

                            # Same satellite
                            if id1 == id2:
                                continue

                            # Canonical ordering prevents:
                            # (1, 2)
                            # (2, 1)
                            #
                            # from becoming two different pairs.

                            pair = tuple(
                                sorted((id1, id2))
                            )

                            candidate_pairs.add(pair)

    return candidate_pairs