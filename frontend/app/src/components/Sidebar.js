import { NavLink } from "react-router-dom";

function Sidebar() {

    return (

        <aside className="sidebar">

            <h1 className="logo">
                Satellite Monitor
            </h1>

            <nav>

                <NavLink to="/">
                    Dashboard
                </NavLink>

                <NavLink to="/satellites">
                    Satellites
                </NavLink>

                <NavLink to="/collisions">
                    Collision Monitor
                </NavLink>

                <NavLink to="/orbit">
                    Orbit Viewer
                </NavLink>

            </nav>

        </aside>
    );
}

export default Sidebar;