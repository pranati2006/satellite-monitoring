import { useEffect, useState } from "react";

import {
    getSatellites,
    fetchSatellites,
    updateSatelliteSelection,
    deleteSatellite,
    deleteMultipleSatellites
} from "../services/api";


function Satellites() {

    const [satellites, setSatellites] = useState([]);
    const [selectedIds, setSelectedIds] = useState([]);
    const [search, setSearch] = useState("");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");


    useEffect(() => {
        loadSatellites();
    }, []);


    const loadSatellites = async () => {

        try {

            setLoading(true);
            setError("");

            const data = await getSatellites();

            setSatellites(data);

        } catch (err) {

            console.error(err);

            setError(
                "Could not load satellites."
            );

        } finally {

            setLoading(false);
        }
    };


    const handleFetch = async () => {

        try {

            setLoading(true);
            setError("");

            await fetchSatellites(10);

            await loadSatellites();

        } catch (err) {

            console.error(err);

            setError(
                "Could not fetch satellites."
            );

        } finally {

            setLoading(false);
        }
    };


    const handleSelect = (id) => {

        setSelectedIds((previous) => {

            if (previous.includes(id)) {

                return previous.filter(
                    (satelliteId) =>
                        satelliteId !== id
                );
            }

            return [
                ...previous,
                id
            ];
        });
    };


    const handleSelectAll = () => {

        const visibleIds =
            filteredSatellites.map(
                (satellite) => satellite.id
            );

        const allSelected =
            visibleIds.every(
                (id) =>
                    selectedIds.includes(id)
            );

        if (allSelected) {

            setSelectedIds(
                selectedIds.filter(
                    (id) =>
                        !visibleIds.includes(id)
                )
            );

        } else {

            setSelectedIds([
                ...new Set([
                    ...selectedIds,
                    ...visibleIds
                ])
            ]);
        }
    };


    const handleToggleActive = async (
        satellite
    ) => {

        try {

            await updateSatelliteSelection(
                satellite.id,
                !satellite.is_active
            );

            setSatellites(
                satellites.map((item) =>
                    item.id === satellite.id
                        ? {
                            ...item,
                            is_active:
                                !item.is_active
                        }
                        : item
                )
            );

        } catch (err) {

            console.error(err);

            setError(
                "Could not update satellite."
            );
        }
    };


    const handleDelete = async (id) => {

        try {

            await deleteSatellite(id);

            setSatellites(
                satellites.filter(
                    (satellite) =>
                        satellite.id !== id
                )
            );

            setSelectedIds(
                selectedIds.filter(
                    (satelliteId) =>
                        satelliteId !== id
                )
            );

        } catch (err) {

            console.error(err);

            setError(
                "Could not delete satellite."
            );
        }
    };


    const handleDeleteSelected = async () => {

        if (selectedIds.length === 0) {
            return;
        }

        try {

            await deleteMultipleSatellites(
                selectedIds
            );

            setSatellites(
                satellites.filter(
                    (satellite) =>
                        !selectedIds.includes(
                            satellite.id
                        )
                )
            );

            setSelectedIds([]);

        } catch (err) {

            console.error(err);

            setError(
                "Could not delete selected satellites."
            );
        }
    };


    const filteredSatellites =
        satellites.filter(
            (satellite) =>
                satellite.name
                    ?.toLowerCase()
                    .includes(
                        search.toLowerCase()
                    ) ||
                String(satellite.norad_id)
                    .includes(search)
        );


    return (

        <div>

            <h1>Satellites</h1>

            <p>
                Manage satellites used for analysis.
            </p>


            <div className="satellite-controls">

                <button onClick={handleFetch}>
                    Fetch Satellites
                </button>

                <input
                    type="text"
                    placeholder="Search by name or NORAD ID"
                    value={search}
                    onChange={(e) =>
                        setSearch(e.target.value)
                    }
                />

                <button
                    onClick={handleDeleteSelected}
                    disabled={
                        selectedIds.length === 0
                    }
                >
                    Delete Selected
                </button>

            </div>


            {selectedIds.length > 0 && (

                <p>
                    {selectedIds.length}
                    {" "}
                    satellite(s) selected
                </p>

            )}


            {loading && (
                <p>Loading...</p>
            )}

            {error && (
                <p>{error}</p>
            )}


            <table>

                <thead>

                    <tr>

                        <th>

                            <input
                                type="checkbox"
                                onChange={handleSelectAll}
                            />

                        </th>

                        <th>ID</th>
                        <th>NORAD ID</th>
                        <th>Name</th>
                        <th>Inclination</th>
                        <th>Eccentricity</th>
                        <th>Mean Motion</th>
                        <th>Active</th>
                        <th>Delete</th>

                    </tr>

                </thead>


                <tbody>

                    {filteredSatellites.map(
                        (satellite) => (

                            <tr key={satellite.id}>

                                <td>

                                    <input
                                        type="checkbox"
                                        checked={
                                            selectedIds.includes(
                                                satellite.id
                                            )
                                        }
                                        onChange={() =>
                                            handleSelect(
                                                satellite.id
                                            )
                                        }
                                    />

                                </td>


                                <td>
                                    {satellite.id}
                                </td>


                                <td>
                                    {satellite.norad_id}
                                </td>


                                <td>
                                    {satellite.name}
                                </td>


                                <td>
                                    {satellite.inclination}
                                </td>


                                <td>
                                    {satellite.eccentricity}
                                </td>


                                <td>
                                    {satellite.mean_motion}
                                </td>


                                <td>

                                    <button
                                        onClick={() =>
                                            handleToggleActive(
                                                satellite
                                            )
                                        }
                                    >
                                        {satellite.is_active
                                            ? "Active"
                                            : "Inactive"}
                                    </button>

                                </td>


                                <td>

                                    <button
                                        onClick={() =>
                                            handleDelete(
                                                satellite.id
                                            )
                                        }
                                    >
                                        Delete
                                    </button>

                                </td>

                            </tr>

                        ))}

                </tbody>

            </table>

        </div>
    );
}


export default Satellites;