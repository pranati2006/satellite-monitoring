from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import (
    AnalysisRun,
    AnalysisSatellite,
    Satellite,
    Conjunction,
    DetailedConjunction
)


# ---------------------------------------------------------
# GET ALL ANALYSES
# ---------------------------------------------------------

def get_all_analyses(db: Session):

    return (
        db.query(AnalysisRun)
        .order_by(AnalysisRun.id.desc())
        .all()
    )


# ---------------------------------------------------------
# GET ONE ANALYSIS
# ---------------------------------------------------------

def get_analysis(db: Session, analysis_id: int):

    return (
        db.query(AnalysisRun)
        .filter(AnalysisRun.id == analysis_id)
        .first()
    )


# ---------------------------------------------------------
# GET SATELLITES BELONGING TO AN ANALYSIS
# ---------------------------------------------------------

def get_analysis_satellites(
    db: Session,
    analysis_id: int
):

    results = (
        db.query(
            Satellite,
            AnalysisSatellite.included
        )
        .join(
            AnalysisSatellite,
            AnalysisSatellite.satellite_id == Satellite.id
        )
        .filter(
            AnalysisSatellite.analysis_id == analysis_id
        )
        .all()
    )

    satellites = []

    for satellite, included in results:

        satellites.append({
            "satellite_id": satellite.id,
            "norad_id": satellite.norad_id,
            "name": satellite.name,
            "included": included
        })

    return satellites


# ---------------------------------------------------------
# SELECT / DESELECT ONE SATELLITE
# ---------------------------------------------------------

def update_satellite_selection(
    db: Session,
    analysis_id: int,
    satellite_id: int,
    included: bool
):

    record = (
        db.query(AnalysisSatellite)
        .filter(
            AnalysisSatellite.analysis_id == analysis_id,
            AnalysisSatellite.satellite_id == satellite_id
        )
        .first()
    )

    if record is None:
        return None

    record.included = included

    db.commit()
    db.refresh(record)

    return record


# ---------------------------------------------------------
# UPDATE MULTIPLE SATELLITES
# ---------------------------------------------------------

def update_multiple_satellite_selection(
    db: Session,
    analysis_id: int,
    satellite_ids: list[int]
):

    records = (
        db.query(AnalysisSatellite)
        .filter(
            AnalysisSatellite.analysis_id == analysis_id
        )
        .all()
    )

    selected_ids = set(satellite_ids)

    for record in records:

        record.included = (
            record.satellite_id in selected_ids
        )

    db.commit()

    return get_analysis_satellites(
        db,
        analysis_id
    )


# ---------------------------------------------------------
# GET CONJUNCTIONS FOR AN ANALYSIS
# ---------------------------------------------------------

def get_analysis_conjunctions(
    db: Session,
    analysis_id: int
):

    conjunctions = (
        db.query(Conjunction)
        .filter(
            Conjunction.analysis_id == analysis_id
        )
        .order_by(
            Conjunction.coarse_tca
        )
        .all()
    )

    results = []

    for conjunction in conjunctions:

        results.append({
            "id": conjunction.id,
            "satellite_1_id": conjunction.satellite_1_id,
            "satellite_2_id": conjunction.satellite_2_id,
            "coarse_tca": conjunction.coarse_tca,
            "minimum_coarse_distance_km":
                conjunction.minimum_coarse_distance_km,
            "conjunction_threshold_km":
                conjunction.conjunction_threshold_km,
            "selected_for_detailed":
                conjunction.selected_for_detailed,
            "status": conjunction.status
        })

    return results


# ---------------------------------------------------------
# GET DETAILED CONJUNCTIONS FOR AN ANALYSIS
# ---------------------------------------------------------

def get_analysis_detailed_conjunctions(
    db: Session,
    analysis_id: int
):

    results = (
        db.query(
            DetailedConjunction,
            Conjunction
        )
        .join(
            Conjunction,
            DetailedConjunction.conjunction_id
            == Conjunction.id
        )
        .filter(
            Conjunction.analysis_id == analysis_id
        )
        .order_by(
            DetailedConjunction.tca
        )
        .all()
    )

    detailed_results = []

    for detailed, conjunction in results:

        detailed_results.append({

            "detailed_conjunction_id":
                detailed.id,

            "conjunction_id":
                conjunction.id,

            "satellite_1_id":
                conjunction.satellite_1_id,

            "satellite_2_id":
                conjunction.satellite_2_id,

            "analysis_start":
                detailed.analysis_start,

            "analysis_end":
                detailed.analysis_end,

            "tca":
                detailed.tca,

            "minimum_distance_km":
                detailed.minimum_distance_km,

            "relative_velocity_km_s":
                detailed.relative_velocity_km_s,

            "risk_level":
                detailed.risk_level,

            "calculated_at":
                detailed.calculated_at
        })

    return detailed_results


# ---------------------------------------------------------
# GET COMPLETE ANALYSIS
# ---------------------------------------------------------

def get_complete_analysis(
    db: Session,
    analysis_id: int
):

    analysis = get_analysis(
        db,
        analysis_id
    )

    if analysis is None:
        return None

    satellites = get_analysis_satellites(
        db,
        analysis_id
    )

    conjunctions = get_analysis_conjunctions(
        db,
        analysis_id
    )

    detailed_conjunctions = (
        get_analysis_detailed_conjunctions(
            db,
            analysis_id
        )
    )

    return {

        "analysis": {
            "id": analysis.id,
            "started_at": analysis.started_at,
            "completed_at": analysis.completed_at,
            "prediction_start": analysis.prediction_start,
            "prediction_end": analysis.prediction_end,
            "screening_interval_seconds":
                analysis.screening_interval_seconds,
            "total_satellites":
                analysis.total_satellites,
            "conjunction_count":
                analysis.conjunction_count,
            "status":
                analysis.status,
            "error_message":
                analysis.error_message
        },

        "satellites": satellites,

        "conjunctions": conjunctions,

        "detailed_conjunctions":
            detailed_conjunctions
    }