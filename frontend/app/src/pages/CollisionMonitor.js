import { useEffect, useState } from "react";

import {
    runCollisionAnalysis,
    runDetailedCollision,
    getAnalysisConjunctions,
    getAnalyses
} from "../services/api";


function CollisionMonitor() {

    const [analyses, setAnalyses] = useState([]);
    const [selectedAnalysisId, setSelectedAnalysisId] = useState("");

    const [analysis, setAnalysis] = useState(null);
    const [conjunctions, setConjunctions] = useState([]);

    const [detailedResult, setDetailedResult] = useState(null);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");


    // -----------------------------------------
    // LOAD PREVIOUS ANALYSES
    // -----------------------------------------

    useEffect(() => {
        loadAnalyses();
    }, []);


    const loadAnalyses = async () => {

        try {

            setError("");

            const data = await getAnalyses();

            setAnalyses(data);

        } catch (err) {

            console.error(err);

            setError(
                "Could not load previous analyses."
            );
        }
    };


    // -----------------------------------------
    // SELECT PREVIOUS ANALYSIS
    // -----------------------------------------

    const handleSelectAnalysis = async (analysisId) => {

        if (!analysisId) {
            return;
        }

        try {

            setLoading(true);
            setError("");

            setSelectedAnalysisId(analysisId);
            setDetailedResult(null);

            const conjunctionData =
                await getAnalysisConjunctions(
                    analysisId
                );

            setConjunctions(conjunctionData);

            const selected =
                analyses.find(
                    (item) =>
                        item.id === Number(analysisId)
                );

            setAnalysis(selected || null);

        } catch (err) {

            console.error(err);

            setError(
                "Could not load conjunctions."
            );

        } finally {

            setLoading(false);
        }
    };


    // -----------------------------------------
    // RUN NEW ANALYSIS
    // -----------------------------------------

    const handleRunNewAnalysis = async () => {

        try {

            setLoading(true);
            setError("");

            setDetailedResult(null);
            setConjunctions([]);

            const result =
                await runCollisionAnalysis();

            setAnalysis(result);
            setSelectedAnalysisId(
                result.analysis_id
            );

            const conjunctionData =
                await getAnalysisConjunctions(
                    result.analysis_id
                );

            setConjunctions(conjunctionData);

            // Refresh previous analyses
            const updatedAnalyses =
                await getAnalyses();

            setAnalyses(updatedAnalyses);

        } catch (err) {

            console.error(err);

            setError(
                err.response?.data?.detail ||
                "Could not run collision analysis."
            );

        } finally {

            setLoading(false);
        }
    };


    // -----------------------------------------
    // DETAILED ANALYSIS
    // -----------------------------------------

    const handleDetailedAnalysis = async (
        conjunctionId
    ) => {

        try {

            setLoading(true);
            setError("");

            const result =
                await runDetailedCollision(
                    conjunctionId
                );

            setDetailedResult(result);

        } catch (err) {

            console.error(err);

            setError(
                err.response?.data?.detail ||
                "Could not run detailed analysis."
            );

        } finally {

            setLoading(false);
        }
    };


    return (

        <div>

            <h1>Collision Monitor</h1>

            <p>
                Detect and analyze satellite conjunctions.
            </p>


            {/* -------------------------------- */}
            {/* NEW / PREVIOUS ANALYSIS */}
            {/* -------------------------------- */}

            <div className="card">

                <h2>Analysis</h2>

                <button
                    onClick={handleRunNewAnalysis}
                    disabled={loading}
                >
                    {loading
                        ? "Running..."
                        : "Run New Analysis"}
                </button>


                <div className="analysis-selector">

                    <label>
                        View Previous Analysis:
                    </label>

                    <select
                        value={selectedAnalysisId}
                        onChange={(e) =>
                            handleSelectAnalysis(
                                e.target.value
                            )
                        }
                    >

                        <option value="">
                            Select Analysis
                        </option>

                        {analyses.map(
                            (item) => (

                                <option
                                    key={item.id}
                                    value={item.id}
                                >
                                    Analysis #{item.id}
                                    {" - "}
                                    {item.status}
                                </option>

                            ))}

                    </select>

                </div>

            </div>


            {/* -------------------------------- */}
            {/* ERROR */}
            {/* -------------------------------- */}

            {error && (

                <div className="error-message">
                    {error}
                </div>

            )}


            {/* -------------------------------- */}
            {/* ANALYSIS SUMMARY */}
            {/* -------------------------------- */}

            {analysis && (

                <div className="card">

                    <h2>
                        Analysis #{analysis.id ||
                            analysis.analysis_id}
                    </h2>

                    <p>
                        Status: {analysis.status}
                    </p>

                    <p>
                        Total Satellites:{" "}
                        {analysis.total_satellites}
                    </p>

                    <p>
                        Conjunctions:{" "}
                        {analysis.conjunction_count}
                    </p>

                    <p>
                        Prediction Start:{" "}
                        {analysis.prediction_start ||
                            analysis.analysis_start}
                    </p>

                    <p>
                        Prediction End:{" "}
                        {analysis.prediction_end ||
                            analysis.analysis_end}
                    </p>

                </div>

            )}


            {/* -------------------------------- */}
            {/* CONJUNCTIONS */}
            {/* -------------------------------- */}

            {selectedAnalysisId && (

                <div>

                    <h2>
                        Conjunctions
                    </h2>


                    {loading && (
                        <p>
                            Loading...
                        </p>
                    )}


                    {!loading &&
                        conjunctions.length === 0 && (

                            <div className="card">

                                <p>
                                    No conjunctions found
                                    for this analysis.
                                </p>

                            </div>

                        )}


                    {conjunctions.length > 0 && (

                        <table>

                            <thead>

                                <tr>

                                    <th>
                                        ID
                                    </th>

                                    <th>
                                        Satellite 1
                                    </th>

                                    <th>
                                        Satellite 2
                                    </th>

                                    <th>
                                        Coarse TCA
                                    </th>

                                    <th>
                                        Coarse Distance (km)
                                    </th>

                                    <th>
                                        Status
                                    </th>

                                    <th>
                                        Action
                                    </th>

                                </tr>

                            </thead>


                            <tbody>

                                {conjunctions.map(
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
                                                    conjunction
                                                        .satellite_1_id
                                                }
                                            </td>

                                            <td>
                                                {
                                                    conjunction
                                                        .satellite_2_id
                                                }
                                            </td>

                                            <td>
                                                {
                                                    conjunction
                                                        .coarse_tca
                                                }
                                            </td>

                                            <td>
                                                {
                                                    conjunction
                                                        .minimum_coarse_distance_km
                                                }
                                            </td>

                                            <td>
                                                {
                                                    conjunction
                                                        .status
                                                }
                                            </td>

                                            <td>

                                                <button
                                                    onClick={() =>
                                                        handleDetailedAnalysis(
                                                            conjunction.id
                                                        )
                                                    }
                                                    disabled={
                                                        loading
                                                    }
                                                >
                                                    Detailed Analysis
                                                </button>

                                            </td>

                                        </tr>

                                    ))}

                            </tbody>

                        </table>

                    )}

                </div>

            )}


            {/* -------------------------------- */}
            {/* DETAILED RESULT */}
            {/* -------------------------------- */}

            {detailedResult && (

                <div className="card detailed-result">

                    <h2>
                        Detailed Analysis Result
                    </h2>

                    <p>
                        Conjunction ID:{" "}
                        {
                            detailedResult
                                .conjunction_id
                        }
                    </p>

                    <p>
                        Satellite 1:{" "}
                        {
                            detailedResult
                                .satellite_1
                        }
                    </p>

                    <p>
                        Satellite 2:{" "}
                        {
                            detailedResult
                                .satellite_2
                        }
                    </p>

                    <p>
                        TCA:{" "}
                        {
                            detailedResult.tca
                        }
                    </p>

                    <p>
                        Minimum Distance:{" "}
                        {
                            detailedResult
                                .minimum_distance_km
                        }
                        {" "}km
                    </p>

                    <p>
                        Status:{" "}
                        {
                            detailedResult.status
                        }
                    </p>

                </div>

            )}

        </div>
    );
}


export default CollisionMonitor;