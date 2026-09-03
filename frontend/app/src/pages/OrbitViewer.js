
import { useState } from "react";

import {
    Viewer,
    Entity
} from "resium";

import {
    Cartesian3,
    Color,
    HeightReference,
    Ion,
    EllipsoidGeometry,
    GeometryInstance,
    Primitive as CesiumPrimitive,
    PerInstanceColorAppearance,
    ColorGeometryInstanceAttribute
} from "cesium";

import { getSatellitePositions } from "../services/api";

Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6ImU3MEtXaHlVekhRdkl4akIiLCJqdGkiOiI3M2QwYWVhMC01ZDZlLTQ1YzktOWQ5Mi0yMmUzODI3ODA5NTUiLCJpZCI6NDc5NTA4LCJpc3MiOiJodHRwczovL2FwaS5jZXNpdW0uY29tIiwiYXVkIjoidW5kZWZpbmVkX2RlZmF1bHQiLCJpYXQiOjE3ODg0MDc2ODJ9.zQ3gG7ZgHofgAZwB1VxUejmePGEuJSI8o70cZUDzsl4";


function OrbitViewer() {

    const [time, setTime] = useState("");

    const [satellites, setSatellites] = useState([]);

    const [selectedSatellite, setSelectedSatellite] =
        useState(null);

    const [trackedSatellite, setTrackedSatellite] =
        useState(null);

    const [noradInput, setNoradInput] = useState("");

    const [loading, setLoading] = useState(false);

    const [error, setError] = useState("");

    const [viewer, setViewer] = useState(null);

    const generateEarthPoints = () => {
        const points = [];

        const earthRadius = 6371000; // meters

        for (let latitude = -90; latitude <= 90; latitude += 5) {
            for (let longitude = -180; longitude < 180; longitude += 5) {

                const lat = latitude * Math.PI / 180;
                const lon = longitude * Math.PI / 180;

                const x =
                    earthRadius *
                    Math.cos(lat) *
                    Math.cos(lon);

                const y =
                    earthRadius *
                    Math.cos(lat) *
                    Math.sin(lon);

                const z =
                    earthRadius *
                    Math.sin(lat);

                points.push(
                    <Entity
                        key={`earth-${latitude}-${longitude}`}
                        position={new Cartesian3(x, y, z)}
                        point={{
                            pixelSize: 3,
                            color: Color.RED
                        }}
                    />
                );
            }
        }

        return points;
    };


    // -----------------------------------------------------
    // DISPLAY SATELLITES
    // -----------------------------------------------------

    const handleDisplay = async () => {

        if (!time) {
            setError("Please select a time.");
            return;
        }

        try {

            setLoading(true);
            setError("");

            const result =
                await getSatellitePositions(time);

            setSatellites(result.satellites);

            setSelectedSatellite(null);
            setTrackedSatellite(null);

        } catch (err) {

            console.error(err);

            setError(
                err.response?.data?.detail ||
                "Could not load satellite positions."
            );

        } finally {

            setLoading(false);

        }
    };


    // -----------------------------------------------------
    // CLICK SATELLITE
    // -----------------------------------------------------

    const handleSatelliteClick = (
        satellite
    ) => {

        setSelectedSatellite(
            satellite
        );

    };


    // -----------------------------------------------------
    // TRACK SATELLITE
    // -----------------------------------------------------

    const handleTrack = () => {

        if (trackedSatellite) {

            setTrackedSatellite(null);

            return;
        }

        const norad =
            noradInput.trim();

        if (!norad) {

            setError(
                "Enter a NORAD ID."
            );

            return;
        }

        const satellite =
            satellites.find(
                (item) =>
                    String(item.norad_id) === norad
            );

        if (!satellite) {

            setError(
                "Satellite with this NORAD ID was not found."
            );

            return;
        }

        setError("");

        setTrackedSatellite(
            satellite
        );

        setSelectedSatellite(
            satellite
        );

    };


    // -----------------------------------------------------
    // SATELLITE POSITION
    // -----------------------------------------------------

    const getPosition = (
        satellite
    ) => {

        return Cartesian3.fromElements(
            satellite.position.x * 1000,
            satellite.position.y * 1000,
            satellite.position.z * 1000
        );

    };


    return (
        <div className="orbit-page">

            <div className="orbit-header">

                <div>
                    <h1>Orbit Viewer</h1>

                    <p>
                        View satellite positions
                        at a specific time.
                    </p>
                </div>

            </div>


            {/* ------------------------------------------------ */}
            {/* CONTROLS */}
            {/* ------------------------------------------------ */}

            <div className="card orbit-controls-card">

                <div className="orbit-control-group">

                    <label>
                        Select Time
                    </label>

                    <input
                        type="datetime-local"
                        value={time}
                        onChange={(e) =>
                            setTime(e.target.value)
                        }
                    />

                    <button
                        className="primary-button"
                        onClick={handleDisplay}
                        disabled={loading}
                    >
                        {loading
                            ? "Loading..."
                            : "Display Satellites"}
                    </button>

                </div>


                <div className="orbit-control-group">

                    <label>
                        NORAD ID
                    </label>

                    <input
                        type="text"
                        placeholder="Enter NORAD ID"
                        value={noradInput}
                        onChange={(e) =>
                            setNoradInput(
                                e.target.value
                            )
                        }
                    />

                    <button
                        className={
                            trackedSatellite
                                ? "danger-button"
                                : "primary-button"
                        }
                        onClick={handleTrack}
                        disabled={
                            satellites.length === 0
                        }
                    >
                        {trackedSatellite
                            ? "✕"
                            : "Track"}
                    </button>

                </div>

            </div>


            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}


            {/* ------------------------------------------------ */}
            {/* CESIUM */}
            {/* ------------------------------------------------ */}

            <div className="orbit-viewer-wrapper">

                <Viewer
                    animation={false}
                    timeline={false}
                    navigationHelpButton={false}
                    homeButton={true}
                    sceneModePicker={false}
                    geocoder={false}
                    baseLayerPicker={false}
                    fullscreenButton={false}
                    vrButton={false}
                    infoBox={false}
                    selectionIndicator={false}
                >

                    {/* RED EARTH SURFACE */}
                    {generateEarthPoints()}

                    {/* SATELLITES */}
                    {satellites.map((satellite) => {
                        const isTracked =
                            trackedSatellite?.norad_id === satellite.norad_id;

                        return (
                            <Entity
                                key={satellite.satellite_id}
                                name={satellite.name}
                                position={getPosition(satellite)}
                                point={{
                                    pixelSize: isTracked ? 16 : 8,
                                    color: isTracked
                                        ? Color.YELLOW
                                        : Color.CYAN,
                                    outlineColor: Color.WHITE,
                                    outlineWidth: isTracked ? 2 : 0,
                                    heightReference: HeightReference.NONE
                                }}
                                onClick={() =>
                                    handleSatelliteClick(satellite)
                                }
                            />
                        );
                    })}

                </Viewer>
            </div>

            {/* ------------------------------------------------ */}
            {/* SATELLITE INFORMATION */}
            {/* ------------------------------------------------ */}

            {selectedSatellite && (

                <div className="card satellite-info-panel">

                    <div className="satellite-info-header">

                        <div>

                            <h2>
                                {selectedSatellite.name}
                            </h2>

                            <p>
                                NORAD ID:{" "}
                                <strong>
                                    {
                                        selectedSatellite.norad_id
                                    }
                                </strong>
                            </p>

                        </div>

                        <button
                            onClick={() =>
                                setSelectedSatellite(
                                    null
                                )
                            }
                        >
                            ✕
                        </button>

                    </div>


                    <div className="satellite-info-grid">

                        <div>
                            <span>Satellite ID</span>
                            <strong>
                                {
                                    selectedSatellite
                                        .satellite_id
                                }
                            </strong>
                        </div>

                        <div>
                            <span>NORAD ID</span>
                            <strong>
                                {
                                    selectedSatellite
                                        .norad_id
                                }
                            </strong>
                        </div>

                        <div>
                            <span>Inclination</span>
                            <strong>
                                {
                                    selectedSatellite
                                        .inclination
                                }°
                            </strong>
                        </div>

                        <div>
                            <span>Eccentricity</span>
                            <strong>
                                {
                                    selectedSatellite
                                        .eccentricity
                                }
                            </strong>
                        </div>

                        <div>
                            <span>RAAN</span>
                            <strong>
                                {
                                    selectedSatellite
                                        .raan
                                }°
                            </strong>
                        </div>

                        <div>
                            <span>Argument of Perigee</span>
                            <strong>
                                {
                                    selectedSatellite
                                        .arg_perigee
                                }°
                            </strong>
                        </div>

                        <div>
                            <span>Mean Anomaly</span>
                            <strong>
                                {
                                    selectedSatellite
                                        .mean_anomaly
                                }°
                            </strong>
                        </div>

                        <div>
                            <span>Mean Motion</span>
                            <strong>
                                {
                                    selectedSatellite
                                        .mean_motion
                                } rev/day
                            </strong>
                        </div>

                    </div>

                </div>

            )}

        </div>
    );
}

export default OrbitViewer;