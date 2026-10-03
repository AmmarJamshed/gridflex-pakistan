import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import ConsumerPage from "./pages/ConsumerPage";
import AggregatorPage from "./pages/AggregatorPage";
import MarketPage from "./pages/MarketPage";
import GridPage from "./pages/GridPage";
import AdminPage from "./pages/AdminPage";
import SimulationPage from "./pages/SimulationPage";
import RegulatoryPage from "./pages/RegulatoryPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/consumer" element={<ConsumerPage />} />
        <Route path="/aggregator" element={<AggregatorPage />} />
        <Route path="/market" element={<MarketPage />} />
        <Route path="/grid" element={<GridPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/simulation" element={<SimulationPage />} />
        <Route path="/regulatory" element={<RegulatoryPage />} />
      </Route>
    </Routes>
  );
}