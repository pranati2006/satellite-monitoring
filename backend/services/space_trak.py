import os
import requests

from dotenv import load_dotenv


load_dotenv()


USERNAME = os.getenv("SPACETRACK_USERNAME")
PASSWORD = os.getenv("SPACETRACK_PASSWORD")


LOGIN_URL = "https://www.space-track.org/ajaxauth/login"

DATA_URL = (
    "https://www.space-track.org/basicspacedata/query/"
    "class/gp/"
    "decay_date/null-val/"
    "orderby/norad_cat_id/"
    "format/json"
)


def login():

    session = requests.Session()

    response = session.post(
        LOGIN_URL,
        data={
            "identity": USERNAME,
            "password": PASSWORD
        },
        timeout=30
    )

    response.raise_for_status()

    return session


def fetch_satellites(limit=10):

    session = login()

    url = DATA_URL + f"/limit/{limit}"

    response = session.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    return response.json()