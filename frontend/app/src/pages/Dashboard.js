import { useEffect, useState } from "react";
import {
    getAnalyses,
    getCompleteAnalysis,
    deleteAnalysis
} from "../services/api";

function Dashboard() {
    const [analyses, setAnalyses] = useState([]);
    const [selectedAnalysis, setSelectedAnalysis] = useState(null);
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        loadAnalyses();
    }, []);

    const loadAnalyses = async () => {
        try {
            setLoading(true);
            setError("");

            const data = await getAnalyses();

            setAnalyses(data);
        } catch (err) {
            console.error(err);
            setError("Could not load analyses.");
        } finally {
            setLoading(false);
        }
    };

    const handleAnalysisClick = async (analysisId) => {
        try {
            setLoading(true);
            setError("");

            const data = await getCompleteAnalysis(analysisId);

            setSelectedAnalysis(data);
        } catch (err) {
            console.error(err);
            setError("Could not load analysis details.");
        } finally {
            setLoading(false);
        }
    };

    const closeOverlay = () => {
        setSelectedAnalysis(null);
        setSearch("");
    };

    const handleDeleteAnalysis = async () => {
        if (!selectedAnalysis) return;

        const analysisId = selectedAnalysis.analysis.id;

        const confirmed = window.confirm(
            `Are you sure you want to delete Analysis #${analysisId}?`
        );

        if (!confirmed) return;

        try {
            setLoading(true);
            setError("");

            await deleteAnalysis(analysisId);

            setAnalyses(
                analyses.filter(
                    (analysis) => analysis.id !== analysisId
                )
            );

            closeOverlay();
        } catch (err) {
            console.error(err);
            setError(
                err.response?.data?.detail ||
                "Could not delete analysis."
            );
        } finally {
            setLoading(false);
        }
    };

    const filteredSatellites =
        selectedAnalysis?.satellites.filter(
            (satellite) =>
                satellite.name
                    ?.toLowerCase()
                    .includes(search.toLowerCase()) ||
                String(satellite.norad_id).includes(search)
        ) || [];

    return (
        <div>
            <h1>Dashboard</h1>

            <p>Previous satellite analyses</p>

            {loading && !selectedAnalysis && (
                <p>Loading analyses...</p>
            )}

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {!loading && analyses.length === 0 && (
                <p>No analyses found.</p>
            )}

            <div className="analysis-list">
                {analyses.map((analysis) => (
                    <div
                        className="card analysis-card"
                        key={analysis.id}
                        onClick={() =>
                            handleAnalysisClick(analysis.id)
                        }
                    >
                        <h3>
                            Analysis #{analysis.id}
                        </h3>

                        <p>
                            Status: {analysis.status}
                        </p>

                        <p>
                            Satellites:{" "}
                            {analysis.total_satellites}
                        </p>

                        <p>
                            Conjunctions:{" "}
                            {analysis.conjunction_count}
                        </p>
                    </div>
                ))}
            </div>

            {/* ------------------------------------------------ */}
            {/* ANALYSIS OVERLAY */}
            {/* ------------------------------------------------ */}

            {selectedAnalysis && (
                <div className="overlay">
                    <div className="overlay-content">

                        <div className="overlay-header">
                            <h2>
                                Analysis #
                                {selectedAnalysis.analysis.id}
                            </h2>

                            <button
                                onClick={closeOverlay}
                            >
                                ✕
                            </button>
                        </div>

                        {/* ------------------------------------ */}
                        {/* ANALYSIS INFORMATION */}
                        {/* ------------------------------------ */}

                        <div className="card">
                            <h3>Analysis Details</h3>

                            <p>
                                <strong>Status:</strong>{" "}
                                {selectedAnalysis.analysis.status}
                            </p>

                            <p>
                                <strong>Started:</strong>{" "}
                                {selectedAnalysis.analysis.started_at}
                            </p>

                            <p>
                                <strong>Completed:</strong>{" "}
                                {selectedAnalysis.analysis.completed_at}
                            </p>

                            <p>
                                <strong>Prediction Start:</strong>{" "}
                                {selectedAnalysis.analysis.prediction_start}
                            </p>

                            <p>
                                <strong>Prediction End:</strong>{" "}
                                {selectedAnalysis.analysis.prediction_end}
                            </p>

                            <p>
                                <strong>Screening Interval:</strong>{" "}
                                {selectedAnalysis.analysis
                                    .screening_interval_seconds}{" "}
                                seconds
                            </p>

                            <p>
                                <strong>Total Satellites:</strong>{" "}
                                {selectedAnalysis.analysis
                                    .total_satellites}
                            </p>

                            <p>
                                <strong>Conjunctions:</strong>{" "}
                                {selectedAnalysis.analysis
                                    .conjunction_count}
                            </p>

                            {selectedAnalysis.analysis.error_message && (
                                <p>
                                    <strong>Error:</strong>{" "}
                                    {selectedAnalysis.analysis
                                        .error_message}
                                </p>
                            )}
                        </div>

                        {/* ------------------------------------ */}
                        {/* SATELLITES */}
                        {/* ------------------------------------ */}

                        <div className="card">
                            <h3>
                                Satellites (
                                {selectedAnalysis.satellites.length}
                                )
                            </h3>

                            <input
                                type="text"
                                placeholder="Search satellite by name or NORAD ID"
                                value={search}
                                onChange={(e) =>
                                    setSearch(e.target.value)
                                }
                            />

                            {filteredSatellites.length === 0 ? (
                                <p>
                                    No satellites found.
                                </p>
                            ) : (
                                <table>
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>NORAD ID</th>
                                            <th>Name</th>
                                            <th>Included</th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {filteredSatellites.map(
                                            (satellite) => (
                                                <tr
                                                    key={
                                                        satellite.satellite_id
                                                    }
                                                >
                                                    <td>
                                                        {
                                                            satellite.satellite_id
                                                        }
                                                    </td>

                                                    <td>
                                                        {
                                                            satellite.norad_id
                                                        }
                                                    </td>

                                                    <td>
                                                        {
                                                            satellite.name
                                                        }
                                                    </td>

                                                    <td>
                                                        {satellite.included
                                                            ? "Yes"
                                                            : "No"}
                                                    </td>
                                                </tr>
                                            )
                                        )}
                                    </tbody>
                                </table>
                            )}
                        </div>

                        {/* ------------------------------------ */}
                        {/* CONJUNCTIONS */}
                        {/* ------------------------------------ */}

                        <div className="card">
                            <h3>
                                Conjunctions (
                                {
                                    selectedAnalysis
                                        .conjunctions.length
                                }
                                )
                            </h3>

                            {selectedAnalysis.conjunctions
                                .length === 0 ? (
                                <p>
                                    No conjunctions found.
                                </p>
                            ) : (
                                <table>
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>Satellite 1</th>
                                            <th>Satellite 2</th>
                                            <th>Coarse TCA</th>
                                            <th>
                                                Distance (km)
                                            </th>
                                            <th>
                                                Threshold (km)
                                            </th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {selectedAnalysis.conjunctions.map(
                                            (conjunction) => (
                                                <tr
                                                    key={
                                                        conjunction.id
                                                    }
                                                >
                                                    <td>
                                                        {
                                                            conjunction.id
                                                        }
                                                    </td>

                                                    <td>
                                                        {
                                                            conjunction.satellite_1_id
                                                        }
                                                    </td>

                                                    <td>
                                                        {
                                                            conjunction.satellite_2_id
                                                        }
                                                    </td>

                                                    <td>
                                                        {
                                                            conjunction.coarse_tca
                                                        }
                                                    </td>

                                                    <td>
                                                        {
                                                            conjunction.minimum_coarse_distance_km
                                                        }
                                                    </td>

                                                    <td>
                                                        {
                                                            conjunction.conjunction_threshold_km
                                                        }
                                                    </td>

                                                    <td>
                                                        {
                                                            conjunction.status
                                                        }
                                                    </td>
                                                </tr>
                                            )
                                        )}
                                    </tbody>
                                </table>
                            )}
                        </div>

                        {/* ------------------------------------ */}
                        {/* DETAILED CONJUNCTIONS */}
                        {/* ------------------------------------ */}

                        <div className="card">
                            <h3>
                                Detailed Conjunctions (
                                {
                                    selectedAnalysis
                                        .detailed_conjunctions
                                        .length
                                }
                                )
                            </h3>

                            {selectedAnalysis
                                .detailed_conjunctions.length === 0 ? (
                                <p>
                                    No detailed conjunctions
                                    available.
                                </p>
                            ) : (
                                <table>
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>
                                                Conjunction ID
                                            </th>
                                            <th>
                                                Satellite 1
                                            </th>
                                            <th>
                                                Satellite 2
                                            </th>
                                            <th>TCA</th>
                                            <th>
                                                Minimum Distance
                                                (km)
                                            </th>
                                            <th>
                                                Relative Velocity
                                                (km/s)
                                            </th>
                                            <th>
                                                Risk Level
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {selectedAnalysis
                                            .detailed_conjunctions
                                            .map(
                                                (detailed) => (
                                                    <tr
                                                        key={
                                                            detailed.detailed_conjunction_id
                                                        }
                                                    >
                                                        <td>
                                                            {
                                                                detailed.detailed_conjunction_id
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                detailed.conjunction_id
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                detailed.satellite_1_id
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                detailed.satellite_2_id
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                detailed.tca
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                detailed.minimum_distance_km
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                detailed.relative_velocity_km_s ??
                                                                "-"
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                detailed.risk_level ??
                                                                "-"
                                                            }
                                                        </td>
                                                    </tr>
                                                )
                                            )}
                                    </tbody>
                                </table>
                            )}
                        </div>

                        {/* ------------------------------------ */}
                        {/* DELETE */}
                        {/* ------------------------------------ */}

                        <div className="overlay-actions">
                            <button
                                onClick={
                                    handleDeleteAnalysis
                                }
                                disabled={loading}
                            >
                                Delete Analysis
                            </button>
                        </div>

                    </div>
                </div>
            )}
        </div>
    );
}

export default Dashboard;