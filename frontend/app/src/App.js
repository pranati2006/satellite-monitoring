import {
  BrowserRouter,
  Routes,
  Route
} from "react-router-dom";

import Sidebar from "./components/Sidebar";

import Dashboard from "./pages/Dashboard";
import Satellites from "./pages/Satellites";
import CollisionMonitor from "./pages/CollisionMonitor";
import OrbitViewer from "./pages/OrbitViewer";

function App() {

  return (

    <BrowserRouter>

      <div className="app">

        <Sidebar />

        <main className="main-content">

          <Routes>

            <Route
              path="/"
              element={<Dashboard />}
            />

            <Route
              path="/satellites"
              element={<Satellites />}
            />

            <Route
              path="/collisions"
              element={<CollisionMonitor />}
            />

            <Route
              path="/orbit"
              element={<OrbitViewer />}
            />

          </Routes>

        </main>

      </div>

    </BrowserRouter>
  );
}

export default App;