from datetime import datetime

from sqlalchemy.orm import Session

from models import Satellite


def save_satellites(
    db: Session,
    satellite_data: list
):

    inserted = 0
    updated = 0

    for data in satellite_data:

        norad_id = int(data["NORAD_CAT_ID"])

        satellite = (
            db.query(Satellite)
            .filter(Satellite.norad_id == norad_id)
            .first()
        )

        epoch = datetime.fromisoformat(
            data["EPOCH"]
        )

        if satellite is None:

            satellite = Satellite(
                norad_id=norad_id,
                name=data["OBJECT_NAME"],

                tle_line1=data["TLE_LINE1"],
                tle_line2=data["TLE_LINE2"],

                epoch=epoch,

                inclination=float(data["INCLINATION"]),
                eccentricity=float(data["ECCENTRICITY"]),
                raan=float(data["RA_OF_ASC_NODE"]),
                arg_perigee=float(data["ARG_OF_PERICENTER"]),
                mean_anomaly=float(data["MEAN_ANOMALY"]),
                mean_motion=float(data["MEAN_MOTION"]),

                data_source="Space-Track",

                is_active=True,

                fetched_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.add(satellite)

            inserted += 1

        else:

            satellite.name = data["OBJECT_NAME"]

            satellite.tle_line1 = data["TLE_LINE1"]
            satellite.tle_line2 = data["TLE_LINE2"]

            satellite.epoch = epoch

            satellite.inclination = float(
                data["INCLINATION"]
            )

            satellite.eccentricity = float(
                data["ECCENTRICITY"]
            )

            satellite.raan = float(
                data["RA_OF_ASC_NODE"]
            )

            satellite.arg_perigee = float(
                data["ARG_OF_PERICENTER"]
            )

            satellite.mean_anomaly = float(
                data["MEAN_ANOMALY"]
            )

            satellite.mean_motion = float(
                data["MEAN_MOTION"]
            )

            satellite.data_source = "Space-Track"

            satellite.is_active = True

            satellite.updated_at = datetime.utcnow()

            updated += 1

    db.commit()

    return {
        "inserted": inserted,
        "updated": updated,
        "total": inserted + updated
    }


# ---------------------------------------------------------
# GET ALL SATELLITES
# ---------------------------------------------------------

def get_all_satellites(
    db: Session
):

    return (
        db.query(Satellite)
        .order_by(Satellite.id)
        .all()
    )


# ---------------------------------------------------------
# GET ONE SATELLITE
# ---------------------------------------------------------

def get_satellite(
    db: Session,
    satellite_id: int
):

    return (
        db.query(Satellite)
        .filter(
            Satellite.id == satellite_id
        )
        .first()
    )


# ---------------------------------------------------------
# UPDATE SATELLITE
# ---------------------------------------------------------

def update_satellite(
    db: Session,
    satellite_id: int,
    name: str | None = None,
    is_active: bool | None = None
):

    satellite = get_satellite(
        db,
        satellite_id
    )

    if satellite is None:
        return None

    if name is not None:
        satellite.name = name

    if is_active is not None:
        satellite.is_active = is_active

    satellite.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(satellite)

    return satellite


# ---------------------------------------------------------
# DELETE SATELLITE
# ---------------------------------------------------------

def delete_satellite(
    db: Session,
    satellite_id: int
):

    satellite = get_satellite(
        db,
        satellite_id
    )

    if satellite is None:
        return None

    db.delete(satellite)
    db.commit()

    return satellite

def delete_multiple_satellites(
    db: Session,
    satellite_ids: list[int]
):

    satellites = (
        db.query(Satellite)
        .filter(Satellite.id.in_(satellite_ids))
        .all()
    )

    if not satellites:
        return []

    for satellite in satellites:
        db.delete(satellite)

    db.commit()

    return [satellite.id for satellite in satellites]

def delete_satellites_by_count(
    db: Session,
    count: int
):
    satellites = (
        db.query(Satellite)
        .order_by(Satellite.id)
        .limit(count)
        .all()
    )

    deleted_ids = [satellite.id for satellite in satellites]

    for satellite in satellites:
        db.delete(satellite)

    db.commit()

    return deleted_ids