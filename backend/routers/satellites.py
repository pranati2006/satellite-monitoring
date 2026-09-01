from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.satellite_service import (
    save_satellites,
    get_all_satellites,
    get_satellite,
    update_satellite,
    delete_satellite,
    delete_multiple_satellites
)
from services.space_trak import fetch_satellites


router = APIRouter(
    prefix="/satellites",
    tags=["Satellites"]
)


# ---------------------------------------------------------
# GET ALL SATELLITES
# ---------------------------------------------------------

@router.get("/")
def get_satellites(
    db: Session = Depends(get_db)
):

    return get_all_satellites(db)


# ---------------------------------------------------------
# GET ONE SATELLITE
# ---------------------------------------------------------

@router.get("/{satellite_id}")
def get_one_satellite(
    satellite_id: int,
    db: Session = Depends(get_db)
):

    satellite = get_satellite(
        db,
        satellite_id
    )

    if satellite is None:
        raise HTTPException(
            status_code=404,
            detail="Satellite not found"
        )

    return satellite


# ---------------------------------------------------------
# FETCH SATELLITES FROM SPACE-TRACK
# ---------------------------------------------------------

@router.post("/fetch")
def fetch_and_save_satellites(
    limit: int = 10,
    db: Session = Depends(get_db)
):

    satellite_data = fetch_satellites(
        limit=limit
    )

    result = save_satellites(
        db,
        satellite_data
    )

    return {
        "message": "Satellites fetched successfully",
        "fetched": len(satellite_data),
        "inserted": result["inserted"],
        "updated": result["updated"],
        "total": result["total"]
    }


# ---------------------------------------------------------
# UPDATE SATELLITE
# ---------------------------------------------------------

@router.put("/{satellite_id}")
def edit_satellite(
    satellite_id: int,
    name: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db)
):

    satellite = update_satellite(
        db,
        satellite_id,
        name,
        is_active
    )

    if satellite is None:
        raise HTTPException(
            status_code=404,
            detail="Satellite not found"
        )

    return {
        "message": "Satellite updated successfully",
        "satellite": satellite
    }


# ---------------------------------------------------------
# DELETE SATELLITE
# ---------------------------------------------------------



@router.delete("/bulk")
def remove_multiple_satellites(
    satellite_ids: list[int],
    db: Session = Depends(get_db)
):

    deleted_ids = delete_multiple_satellites(
        db,
        satellite_ids
    )

    return {
        "message": "Satellites deleted successfully",
        "deleted_satellite_ids": deleted_ids,
        "count": len(deleted_ids)
    }

@router.delete("/{satellite_id}")
def remove_satellite(
    satellite_id: int,
    db: Session = Depends(get_db)
):

    satellite = delete_satellite(
        db,
        satellite_id
    )

    if satellite is None:
        raise HTTPException(
            status_code=404,
            detail="Satellite not found"
        )

    return {
        "message": "Satellite deleted successfully",
        "satellite_id": satellite_id
    }