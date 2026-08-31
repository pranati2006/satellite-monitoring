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