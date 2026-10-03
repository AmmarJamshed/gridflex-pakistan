import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import Stat from "../components/Stat";
import ConditionChip from "../components/ConditionChip";

export default function GridPage() {
  const { login } = useAuth();
  const [status, setStatus] = useState<any>(null);
  const [forecasts, setForecasts] = useState<any>(null);
  const [dr, setDr] = useState<any[]>([]);

  async function load() {
    const [s, f, d] = await Promise.all([api.gridStatus(), api.forecasts(), api.drEvents()]);
    setStatus(s);
    setForecasts(f);
    setDr(d);
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  async function congest(code: string) {
    await login("utility@gridflex.pk", "demo1234");
    const token = localStorage.getItem("gf_token");
    if (!token) return;
    await api.triggerCongestion(token, code);
    await load();
  }

  const demand24 = forecasts?.demand?.horizons?.["24h"] ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold">Utility / grid operator</h1>
        <p className="text-sm text-flex-ink/60">
          Illustrative Grid Model — Not an operational representation of Pakistan&apos;s transmission network.
        </p>
      </div>

      {status ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Stat label="Current demand" value={`${status.current_demand_mw} MW`} tone="blue" />
            <Stat label="Available flexibility" value={`${status.available_flexibility_mw} MW`} tone="green" />
            <Stat label="Peak demand" value={`${status.peak_demand_mw} MW`} tone="orange" />
            <Stat label="Renewables" value={`${status.renewable_generation_mw} MW`} tone="orange" />
            <Stat label="Battery capacity" value={`${status.battery_capacity_mwh} MWh`} tone="purple" />
            <Stat label="Active DR events" value={status.active_dr_events} tone="red" />
          </div>

          <div className="panel p-5">
            <h2 className="font-display text-xl font-semibold">Conceptual zones</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {status.zones.map((z: any) => (
                <div key={z.code} className="rounded-2xl border border-black/5 bg-flex-mist/60 p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-display font-semibold">{z.city}</div>
                    <ConditionChip condition={z.congestion} />
                  </div>
                  <div className="mt-2 text-xs text-flex-ink/55">{z.disco}</div>
                  <div className="mt-3 text-sm">
                    Demand <strong>{z.demand_mw} MW</strong>
                    <br />
                    Flexibility <strong className="text-flex-green">{z.flexibility_mw} MW</strong>
                  </div>
                  <button type="button" className="btn-warn mt-3 w-full text-xs" onClick={() => congest(z.code)}>
                    Trigger congestion
                  </button>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-4">
          <h3 className="font-display text-lg font-semibold">Demand forecast (24h)</h3>
          <p className="text-xs text-flex-ink/50">Random Forest + linear blend on simulated history</p>
          <ul className="mt-3 max-h-56 space-y-1 overflow-auto text-sm">
            {demand24.slice(0, 12).map((p: any) => (
              <li key={p.step} className="flex justify-between rounded-lg bg-flex-mist/70 px-3 py-1.5">
                <span>+{p.step}h</span>
                <strong>{p.value} MW</strong>
              </li>
            ))}
          </ul>
        </div>
        <div className="panel p-4">
          <h3 className="font-display text-lg font-semibold">Demand-response events</h3>
          <ul className="mt-3 space-y-2 text-sm">
            {dr.map((e) => (
              <li key={e.id} className="rounded-xl border border-black/5 px-3 py-2">
                <div className="font-semibold">{e.title}</div>
                <div className="text-flex-ink/60">
                  Target {e.target_reduction_mw} MW · Achieved {e.achieved_reduction_mw} MW · {e.status}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}