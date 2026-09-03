import axios from "axios";

const API = axios.create({
    baseURL: "http://127.0.0.1:8000"
});


// -----------------------------
// SATELLITES
// -----------------------------

export const getSatellites = async () => {

    const response = await API.get(
        "/satellites/"
    );

    return response.data;
};


export const fetchSatellites = async (limit = 10) => {

    const response = await API.post(
        `/satellites/fetch?limit=${limit}`
    );

    return response.data;
};


// -----------------------------
// COLLISION
// -----------------------------

export const runCollisionAnalysis = async () => {

    const response = await API.post(
        "/collisions/collision/run"
    );

    return response.data;
};


export const runDetailedCollision = async (
    conjunctionId
) => {

    const response = await API.post(
        `/collisions/collision/detailed/run?conjunction_id=${conjunctionId}`
    );

    return response.data;
};


// -----------------------------
// ANALYSIS
// -----------------------------

export const getAnalyses = async () => {

    const response = await API.get(
        "/satellites/analyses/"
    );

    return response.data;
};


export const getAnalysis = async (
    analysisId
) => {

    const response = await API.get(
        `/satellites/analyses/${analysisId}`
    );

    return response.data;
};


export const getAnalysisSatellites = async (
    analysisId
) => {

    const response = await API.get(
        `/satellites/analyses/${analysisId}/satellites`
    );

    return response.data;
};


export const getAnalysisConjunctions = async (
    analysisId
) => {

    const response = await API.get(
        `/satellites/analyses/${analysisId}/conjunctions`
    );

    return response.data;
};


export const getDetailedConjunctions = async (
    analysisId
) => {

    const response = await API.get(
        `/satellites/analyses/${analysisId}/detailed-conjunctions`
    );

    return response.data;
};

export const updateSatelliteSelection = async (
    satelliteId,
    isActive
) => {

    const response = await API.put(
        `/satellites/${satelliteId}`,
        null,
        {
            params: {
                is_active: isActive
            }
        }
    );

    return response.data;
};


export const deleteSatellite = async (
    satelliteId
) => {

    const response = await API.delete(
        `/satellites/${satelliteId}`
    );

    return response.data;
};


export const deleteMultipleSatellites = async (
    satelliteIds
) => {

    const response = await API.delete(
        "/satellites/",
        {
            data: {
                satellite_ids: satelliteIds
            }
        }
    );

    return response.data;
};

export const getCompleteAnalysis = async (analysisId) => {
    const response = await API.get(
        `/satellites/analyses/${analysisId}`
    );

    return response.data;
};
export const deleteAnalysis = async (analysisId) => {
    const response = await API.delete(
        `/satellites/analyses/${analysisId}`
    );

    return response.data;
};

export const getSatellitePositions = async (time) => {
    const response = await API.get(
        "/orbit/positions",
        {
            params: {
                time: time
            }
        }
    );

    return response.data;
};