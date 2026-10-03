import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import Stat from "../components/Stat";

export default function AdminPage() {
  const { login } = useAuth();
  const [config, setConfig] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any>(null);
  const [participants, setParticipants] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    (async () => {
      await login("admin@gridflex.pk", "demo1234");
      const [c, a, an, p] = await Promise.all([
        api.config(),
        api.fraudAlerts(),
        api.anomalies(),
        api.participants(),
      ]);
      setConfig(c);
      setAlerts(a);
      setAnomalies(an);
      setParticipants(p);
    })().catch(console.error);
  }, [login]);

  async function save() {
    const token = localStorage.getItem("gf_token");
    if (!token || !config) return;
    const updated = await api.updateConfig(token, config);
    setConfig(updated);
    setMsg("Configuration saved (prototype parameters).");
  }

  async function injectFraud() {
    const token = localStorage.getItem("gf_token");
    const p = participants[0];
    if (!token || !p) return;
    const base = import.meta.env.VITE_API_URL ?? "";
    const res = await fetch(
      `${base}/api/fraud/check?participant_id=${p.id}&claimed_kwh=500&observed_kwh=20`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    const body = await res.json();
    setMsg(body.flagged ? body.alert.message : body.message);
    setAlerts(await api.fraudAlerts());
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold">Admin / control room</h1>
        <p className="text-flex-ink/65">Economic parameters, fraud monitors, simulation controls.</p>
      </div>

      {config ? (
        <div className="panel p-5">
          <h2 className="font-display text-xl font-semibold">Economic model (configurable)</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {(
              [
                ["platform_fee_pct", "Platform fee"],
                ["grid_fee_pct", "Grid fee"],
                ["normal_price_pkr", "Normal PKR"],
                ["peak_price_pkr", "Peak PKR"],
                ["critical_price_pkr", "Critical PKR"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="text-sm">
                <span className="text-xs text-flex-ink/55">{label}</span>
                <input
                  type="number"
                  step="0.01"
                  className="mt-1 w-full rounded-xl border border-black/10 px-3 py-2"
                  value={config[key]}
                  onChange={(e) => setConfig({ ...config, [key]: Number(e.target.value) })}
                />
              </label>
            ))}
          </div>
          <button type="button" className="btn-primary mt-4" onClick={save}>
            Save parameters
          </button>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Participants (sample)" value={participants.length} tone="blue" />
        <Stat label="Open fraud alerts" value={alerts.length} tone="red" />
        <Stat label="IsolationForest anomalies" value={anomalies?.anomaly_count ?? "—"} tone="orange" />
      </div>

      <div className="panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-xl font-semibold">Fraud / anomaly detection</h2>
          <button type="button" className="btn-warn" onClick={injectFraud}>
            Test invalid 500 kWh claim
          </button>
        </div>
        {msg ? <p className="mt-3 rounded-xl bg-flex-orange/10 px-3 py-2 text-sm text-flex-orange">{msg}</p> : null}
        <ul className="mt-4 space-y-2 text-sm">
          {alerts.map((a) => (
            <li key={a.id} className="rounded-xl border border-flex-red/20 bg-flex-red/5 px-3 py-2">
              <strong>{a.alert_type}</strong> · {a.severity_id ?? "n/a"} — {a.message}
            </li>
          ))}
          {alerts.length === 0 ? <li className="text-flex-ink/50">No alerts yet.</li> : null}
        </ul>
      </div>
    </div>
  );
}