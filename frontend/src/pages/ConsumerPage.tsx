import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import Stat from "../components/Stat";

export default function ConsumerPage() {
  const { token, login } = useAuth();
  const [dash, setDash] = useState<any>(null);
  const [shift, setShift] = useState<any>(null);

  useEffect(() => {
    async function load() {
      let t = token;
      if (!t) {
        await login("consumer@gridflex.pk", "demo1234");
        t = localStorage.getItem("gf_token");
      }
      if (!t) return;
      const d = await api.consumerDashboard(t);
      setDash(d);
      const s = await api.loadShift({
        appliances: { AC: 3, WaterHeater: 2, EV: 7, WashingMachine: 1 },
        peak_window: [18, 21],
        shift_window: [13, 16],
        shift_appliance: "EV",
      });
      setShift(s);
    }
    load().catch(console.error);
  }, [token, login]);

  const curve = shift
    ? shift.before_curve.map((b: number, i: number) => ({
        hour: i,
        before: b,
        after: shift.after_curve[i],
      }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold">Consumer dashboard</h1>
        <p className="text-flex-ink/65">Monitor, offer flexibility, and earn from intelligent load use.</p>
      </div>

      {dash ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Current consumption" value={`${dash.flexibility.current_load_kw} kW`} tone="blue" />
            <Stat label="Today's consumption" value={`${dash.today_consumption_kwh} kWh`} tone="blue" />
            <Stat label="Potential flexibility" value={`${dash.flexibility.available_flexibility_kw} kW`} tone="green" />
            <Stat label="Estimated earnings" value={`PKR ${dash.wallet.earnings_pkr}`} tone="purple" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="panel p-5">
              <h2 className="font-display text-xl font-semibold">Flexibility wallet</h2>
              <ul className="mt-3 space-y-2 text-sm">
                <li>Flexibility provided: <strong>{dash.wallet.flexibility_provided_kwh} kWh</strong></li>
                <li>Demand reduction: <strong>{dash.wallet.demand_reduction_kwh} kWh</strong></li>
                <li>Solar surplus: <strong>{dash.wallet.solar_surplus_kwh} kWh</strong></li>
                <li>Pending settlement: <strong>PKR {dash.wallet.pending_settlement_pkr}</strong></li>
                <li>CO₂ avoided (est.): <strong>{dash.co2_avoided_kg} kg</strong></li>
              </ul>
              <p className="mt-3 text-xs text-flex-ink/55">Fiat PKR credits — not cryptocurrency.</p>
            </div>
            <div className="panel p-5">
              <h2 className="font-display text-xl font-semibold">Load classification</h2>
              <div className="mt-3 h-56">
                <ResponsiveContainer>
                  <BarChart
                    data={[
                      { name: "Essential", kw: dash.flexibility.essential_load_kw },
                      { name: "Shiftable", kw: dash.flexibility.shiftable_kw },
                      { name: "Curtailable", kw: dash.flexibility.curtailable_kw },
                      { name: "Storage", kw: dash.flexibility.storage_kw },
                      { name: "Generation", kw: dash.flexibility.generation_kw },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis unit=" kW" />
                    <Tooltip />
                    <Bar dataKey="kw" fill="#1fa97a" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      ) : (
        <p>Loading consumer view…</p>
      )}

      {shift ? (
        <div className="panel p-5">
          <h2 className="font-display text-xl font-semibold">Smart load shifting</h2>
          <p className="mt-1 text-sm text-flex-ink/65">{shift.narrative}</p>
          <div className="mt-2 flex gap-4 text-sm">
            <span>Before peak: <strong className="text-flex-orange">{shift.before_peak_kw} kW</strong></span>
            <span>After peak: <strong className="text-flex-green">{shift.after_peak_kw} kW</strong></span>
          </div>
          <div className="mt-4 h-72">
            <ResponsiveContainer>
              <LineChart data={curve}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis unit=" kW" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="before" stroke="#c0392b" strokeWidth={2} name="Before" dot={false} />
                <Line type="monotone" dataKey="after" stroke="#1b6ca8" strokeWidth={2} name="After" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : null}
    </div>
  );
}