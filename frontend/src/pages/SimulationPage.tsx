import { useState } from "react";
import { api } from "../lib/api";
import HourlyChart from "../components/HourlyChart";
import Stat from "../components/Stat";

export default function SimulationPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      const data = await api.runSimulation({
        households: 10000,
        commercial: 1000,
        industrial: 100,
        solar_systems: 2000,
        batteries: 500,
        seed: 42,
      });
      setResult(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="panel p-6">
        <h1 className="font-display text-3xl font-semibold">Pakistan GridFlex Simulation</h1>
        <p className="mt-2 max-w-3xl text-flex-ink/70">
          One-click demo: 10,000 households · 1,000 commercial · 100 industrial · 2,000 solar · 500 batteries.
          Compare evening-peak demand <strong>without</strong> and <strong>with</strong> GRIDFLEX coordination.
        </p>
        <button type="button" className="btn-accent mt-4" disabled={loading} onClick={run}>
          {loading ? "Running simulation…" : "RUN PAKISTAN GRIDFLEX SIMULATION"}
        </button>
        {error ? <p className="mt-3 text-sm text-flex-red">{error}</p> : null}
      </div>

      {result ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Peak without" value={`${result.peak_without_mw} MW`} tone="red" />
            <Stat label="Peak with GRIDFLEX" value={`${result.peak_with_mw} MW`} tone="blue" />
            <Stat
              label="Peak reduction"
              value={`${result.peak_reduction_mw} MW (${result.peak_reduction_pct}%)`}
              tone="green"
            />
            <Stat label="Energy shifted" value={`${result.energy_shifted_mwh} MWh`} tone="purple" />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Market volume" value={`${result.market_volume_mwh} MWh`} tone="purple" />
            <Stat label="Participant earnings" value={`PKR ${result.participant_earnings_pkr.toLocaleString()}`} tone="green" />
            <Stat label="Aggregator earnings" value={`PKR ${result.aggregator_earnings_pkr.toLocaleString()}`} tone="blue" />
            <Stat label="System savings (proto)" value={`PKR ${result.system_savings_pkr.toLocaleString()}`} tone="orange" />
          </div>
          <HourlyChart
            without={result.without_gridflex}
            withFlex={result.with_gridflex}
            peakThreshold={result.peak_without_mw * 0.92}
          />
          <div className="panel p-5 text-sm leading-relaxed text-flex-ink/80">{result.story}</div>
        </>
      ) : null}
    </div>
  );
}