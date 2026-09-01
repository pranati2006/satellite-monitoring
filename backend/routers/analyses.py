from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from database import get_db

from services.analysis_service import (
    get_all_analyses,
    get_complete_analysis,
    get_analysis_satellites,
    update_satellite_selection,
    update_multiple_satellite_selection,
    get_analysis_conjunctions,
    get_analysis_detailed_conjunctions
)


router = APIRouter(
    prefix="/satellites/analyses",
    tags=["Analyses"]
)


# ---------------------------------------------------------
# GET ALL ANALYSES
# ---------------------------------------------------------

@router.get("/")
def get_analyses(
    db: Session = Depends(get_db)
):

    analyses = get_all_analyses(db)

    return analyses


# ---------------------------------------------------------
# GET COMPLETE ANALYSIS
# ---------------------------------------------------------

@router.get("/{analysis_id}")
def get_one_analysis(
    analysis_id: int,
    db: Session = Depends(get_db)
):

    result = get_complete_analysis(
        db,
        analysis_id
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )

    return result


# ---------------------------------------------------------
# GET SATELLITES FOR ANALYSIS
# ---------------------------------------------------------

@router.get("/{analysis_id}/satellites")
def get_satellites_for_analysis(
    analysis_id: int,
    db: Session = Depends(get_db)
):

    satellites = get_analysis_satellites(
        db,
        analysis_id
    )

    return satellites


# ---------------------------------------------------------
# SELECT / DESELECT ONE SATELLITE
# ---------------------------------------------------------

@router.put("/{analysis_id}/satellites/{satellite_id}")
def change_satellite_selection(
    analysis_id: int,
    satellite_id: int,
    included: bool,
    db: Session = Depends(get_db)
):

    result = update_satellite_selection(
        db,
        analysis_id,
        satellite_id,
        included
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Satellite is not part of this analysis"
        )

    return {
        "message": "Satellite selection updated",
        "analysis_id": analysis_id,
        "satellite_id": satellite_id,
        "included": result.included
    }


# ---------------------------------------------------------
# SELECT / DESELECT MULTIPLE SATELLITES
# ---------------------------------------------------------

@router.put("/{analysis_id}/satellites")
def change_multiple_satellite_selection(
    analysis_id: int,
    satellite_ids: list[int],
    db: Session = Depends(get_db)
):

    result = update_multiple_satellite_selection(
        db,
        analysis_id,
        satellite_ids
    )

    return {
        "message": "Satellite selections updated",
        "analysis_id": analysis_id,
        "satellites": result
    }


# ---------------------------------------------------------
# GET CONJUNCTIONS FOR ANALYSIS
# ---------------------------------------------------------

@router.get("/{analysis_id}/conjunctions")
def get_conjunctions(
    analysis_id: int,
    db: Session = Depends(get_db)
):

    return get_analysis_conjunctions(
        db,
        analysis_id
    )


# ---------------------------------------------------------
# GET DETAILED CONJUNCTIONS FOR ANALYSIS
# ---------------------------------------------------------

@router.get("/{analysis_id}/detailed-conjunctions")
def get_detailed_conjunctions(
    analysis_id: int,
    db: Session = Depends(get_db)
):

    return get_analysis_detailed_conjunctions(
        db,
        analysis_id
    )