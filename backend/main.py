from fastapi import FastAPI

from routers.satellites import router as satellite_router
from routers.orbit import router as orbit_router
from routers.collision import router as collision_router
from routers.analyses import router as analysis_router


app = FastAPI()


app.include_router(satellite_router)
app.include_router(orbit_router)
app.include_router(collision_router)
app.include_router(analysis_router)


@app.get("/")
def home():
    return {
        "message": "Satellite Monitoring Backend is running"
    }