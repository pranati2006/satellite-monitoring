from fastapi import FastAPI

from routers.satellites import router as satellite_router


app = FastAPI()


app.include_router(satellite_router)


@app.get("/")
def home():
    return {
        "message": "Satellite Monitoring Backend is running"
    }