import numpy as np
from sklearn.cluster import DBSCAN


def find_clusters(
    satellites,
    eps_km,
    min_samples=2
):

    if len(satellites) < 2:
        return []

    coordinates = np.array([
        [
            satellite["position"]["x"],
            satellite["position"]["y"],
            satellite["position"]["z"]
        ]
        for satellite in satellites
    ])

    model = DBSCAN(
        eps=eps_km,
        min_samples=min_samples,
        metric="euclidean"
    )

    labels = model.fit_predict(coordinates)

    clusters = {}

    for satellite, label in zip(satellites, labels):

        # -1 means DBSCAN considers it noise
        if label == -1:
            continue

        if label not in clusters:
            clusters[label] = []

        clusters[label].append(satellite)

    return list(clusters.values())