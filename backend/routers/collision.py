from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AnalysisRun,
    AnalysisSatellite,
    Conjunction,
    DetailedConjunction,
    Satellite
)

from services.satellite_service import save_satellites
from services.space_trak import fetch_satellites
from services.sgp4_service import calculate_position
from services.collision_service import screen_satellites
from services.collision_service import detailed_analysis

from datetime import datetime, timezone, timedelta
from config import (
    SCREENING_EPS_KM,
    SCREENING_INTERVAL_MINUTES,
    PREDICTION_DAYS
)

router = APIRouter(
    prefix="/collisions",
    tags=["Collisions"]
)

@router.post("/collision/run")
def run_collision_analysis(
    db: Session = Depends(get_db)
):

    satellites = db.query(Satellite).filter(
        Satellite.is_active == True
    ).all()

    if not satellites:
        raise HTTPException(
            status_code=404,
            detail="No active satellites found"
        )

    analysis_start = datetime.now(timezone.utc)

    analysis_end = max(
        satellite.epoch.replace(tzinfo=timezone.utc)
        + timedelta(days=PREDICTION_DAYS)
        for satellite in satellites
    )

    # Create analysis run
    analysis = AnalysisRun(
        started_at=analysis_start,
        prediction_start=analysis_start,
        prediction_end=analysis_end,
        screening_interval_seconds=SCREENING_INTERVAL_MINUTES * 60,
        total_satellites=len(satellites),
        status="RUNNING"
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Prepare data for screening service
    satellite_data = []

    for satellite in satellites:

        satellite_data.append({
            "id": satellite.id,
            "norad_id": satellite.norad_id,
            "tle_line1": satellite.tle_line1,
            "tle_line2": satellite.tle_line2,
            "tle_epoch": satellite.epoch.replace(
                tzinfo=timezone.utc
            )
        })

        # Store satellites included in this analysis
        analysis_satellite = AnalysisSatellite(
            analysis_id=analysis.id,
            satellite_id=satellite.id,
            included=True
        )

        db.add(analysis_satellite)

    db.commit()

    # Call existing screening service
    results = screen_satellites(
        satellite_data,
        analysis_start,
        analysis_end,
        eps_km=SCREENING_EPS_KM
    )

    # Store conjunction candidates
    for result in results:

        conjunction = Conjunction(
            analysis_id=analysis.id,
            satellite_1_id=result["satellite_1_id"],
            satellite_2_id=result["satellite_2_id"],
            coarse_tca=result["time"],
            minimum_coarse_distance_km=result["distance_km"],
            conjunction_threshold_km=SCREENING_EPS_KM,
            selected_for_detailed=True,
            status="POSSIBLE"
        )

        db.add(conjunction) 

    analysis.conjunction_count = len(results)
    analysis.completed_at = datetime.now(timezone.utc)
    analysis.status = "COMPLETED"

    db.commit()

    return {
        "analysis_id": analysis.id,
        "status": analysis.status,
        "total_satellites": len(satellites),
        "conjunction_count": len(results),
        "analysis_start": analysis_start,
        "analysis_end": analysis_end
    }

@router.post("/collision/detailed/run")
def run_detailed_collision_analysis(
    conjunction_id: int,
    db: Session = Depends(get_db)
):
    conjunction = (
        db.query(Conjunction)
        .filter(Conjunction.id == conjunction_id)
        .first()
    )

    if not conjunction:
        raise HTTPException(
            status_code=404,
            detail="Conjunction not found"
        )

    # -----------------------------------------------------
    # CHECK IF DETAILED ANALYSIS ALREADY EXISTS
    # -----------------------------------------------------

    existing = (
        db.query(DetailedConjunction)
        .filter(
            DetailedConjunction.conjunction_id == conjunction_id
        )
        .first()
    )

    if existing:
        return {
            "conjunction_id": conjunction.id,
            "satellite_1": conjunction.satellite_1_id,
            "satellite_2": conjunction.satellite_2_id,
            "tca": existing.tca,
            "minimum_distance_km": existing.minimum_distance_km,
            "relative_velocity_km_s": existing.relative_velocity_km_s,
            "risk_level": existing.risk_level,
            "status": "ALREADY_ANALYZED"
        }

    # -----------------------------------------------------
    # GET SATELLITES
    # -----------------------------------------------------

    satellite_1 = (
        db.query(Satellite)
        .filter(Satellite.id == conjunction.satellite_1_id)
        .first()
    )

    satellite_2 = (
        db.query(Satellite)
        .filter(Satellite.id == conjunction.satellite_2_id)
        .first()
    )

    if not satellite_1 or not satellite_2:
        raise HTTPException(
            status_code=404,
            detail="One or both satellites not found"
        )

    # -----------------------------------------------------
    # RUN DETAILED ANALYSIS
    # -----------------------------------------------------

    result = detailed_analysis(
        satellite_1,
        satellite_2,
        conjunction.coarse_tca
    )

    # -----------------------------------------------------
    # SAVE RESULT
    # -----------------------------------------------------

    detailed = DetailedConjunction(
        conjunction_id=conjunction.id,

        analysis_start=(
            conjunction.coarse_tca
            - timedelta(minutes=SCREENING_INTERVAL_MINUTES)
        ),

        analysis_end=(
            conjunction.coarse_tca
            + timedelta(minutes=SCREENING_INTERVAL_MINUTES)
        ),

        tca=result["tca"],

        minimum_distance_km=
            result["minimum_distance_km"],

        calculated_at=datetime.now(timezone.utc)
    )

    db.add(detailed)

    conjunction.selected_for_detailed = True
    conjunction.status = "ANALYZED"

    db.commit()
    db.refresh(detailed)

    return {
        "conjunction_id": conjunction.id,
        "satellite_1": conjunction.satellite_1_id,
        "satellite_2": conjunction.satellite_2_id,
        "tca": detailed.tca,
        "minimum_distance_km": detailed.minimum_distance_km,
        "relative_velocity_km_s": detailed.relative_velocity_km_s,
        "risk_level": detailed.risk_level,
        "status": conjunction.status
    }
@router.post("/collision/detailed/run-batch")
def run_batch_detailed_collision_analysis(
    conjunction_ids: list[int],
    db: Session = Depends(get_db)
):

    results = []

    for conjunction_id in conjunction_ids:

        conjunction = db.query(Conjunction).filter(
            Conjunction.id == conjunction_id
        ).first()

        if not conjunction:
            continue

        satellite_1 = db.query(Satellite).filter(
            Satellite.id == conjunction.satellite_1_id
        ).first()

        satellite_2 = db.query(Satellite).filter(
            Satellite.id == conjunction.satellite_2_id
        ).first()

        if not satellite_1 or not satellite_2:
            continue

        result = detailed_analysis(
            satellite_1,
            satellite_2,
            conjunction.coarse_tca
        )

        # Check if detailed result already exists
        detailed = db.query(DetailedConjunction).filter(
            DetailedConjunction.conjunction_id == conjunction.id
        ).first()

        if detailed:

            detailed.analysis_start = (
                conjunction.coarse_tca
                - timedelta(minutes=SCREENING_INTERVAL_MINUTES)
            )

            detailed.analysis_end = (
                conjunction.coarse_tca
                + timedelta(minutes=SCREENING_INTERVAL_MINUTES)
            )

            detailed.tca = result["tca"]
            detailed.minimum_distance_km = result["minimum_distance_km"]
            detailed.calculated_at = datetime.now(timezone.utc)

        else:

            detailed = DetailedConjunction(
                conjunction_id=conjunction.id,

                analysis_start=(
                    conjunction.coarse_tca
                    - timedelta(minutes=SCREENING_INTERVAL_MINUTES)
                ),

                analysis_end=(
                    conjunction.coarse_tca
                    + timedelta(minutes=SCREENING_INTERVAL_MINUTES)
                ),

                tca=result["tca"],

                minimum_distance_km=result["minimum_distance_km"],

                calculated_at=datetime.now(timezone.utc)
            )

            db.add(detailed)

        conjunction.selected_for_detailed = True
        conjunction.status = "ANALYZED"

        results.append({
            "conjunction_id": conjunction.id,
            "satellite_1_id": conjunction.satellite_1_id,
            "satellite_2_id": conjunction.satellite_2_id,
            "tca": result["tca"],
            "minimum_distance_km": result["minimum_distance_km"],
            "status": conjunction.status
        })

    db.commit()

    return {
        "count": len(results),
        "results": results
    }