from datetime import timedelta


def prepare_time_filtered_batches(satellites, prediction_days=7):
    """
    Temporary baseline:
    Return all satellites as one batch.

    Later we will add:
    1. altitude batching
    2. overlapping altitude bands
    3. time-window filtering
    4. common-time intervals
    """

    if not satellites:
        return []

    start_time = min(
        satellite["tle_epoch"]
        for satellite in satellites
    )

    end_time = start_time + timedelta(days=prediction_days)

    return [
        {
            "satellites": satellites,

            # Required batch parameters
            "altitude_start": None,
            "altitude_end": None,

            "start_time": start_time,
            "end_time": end_time
        }
    ]