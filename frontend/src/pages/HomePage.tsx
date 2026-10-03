import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import Stat from "../components/Stat";

export default function HomePage() {
  const { login, user } = useAuth();
  const [status, setStatus] = useState<any>(null);
  const [concept, setConcept] = useState<any>(null);
  const [email, setEmail] = useState("consumer@gridflex.pk");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");

  useEffect(() => {
    api.gridStatus().then(setStatus).catch(console.error);
    api.concept().then(setConcept).catch(console.error);
  }, []);

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-3xl border border-white/50 bg-[#0e1a24] text-white shadow-panel">
        <div
          className="absolute inset-0 opacity-40"
          style={{
            background:
              "radial-gradient(circle at 20% 20%, #1fa97a 0%, transparent 40%), radial-gradient(circle at 80% 10%, #1b6ca8 0%, transparent 35%), linear-gradient(135deg, #0e1a24, #163247)",
          }}
        />
        <div className="relative grid gap-8 px-6 py-12 md:grid-cols-[1.2fr_0.8fr] md:px-10">
          <div className="rise">
            <div className="font-display text-5xl font-bold tracking-tight md:text-6xl">GRIDFLEX</div>
            <div className="mt-1 font-display text-2xl text-flex-green md:text-3xl">Pakistan</div>
            <p className="mt-4 max-w-xl text-lg text-white/80">
              Turn unused electricity flexibility into value. Shift, store, and coordinate demand —
              without pretending power hops peer-to-peer across the country.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/simulation" className="btn-accent">
                RUN PAKISTAN GRIDFLEX SIMULATION
              </Link>
              <Link to="/market" className="btn-primary">
                Open marketplace
              </Link>
            </div>
          </div>
          <div className="panel bg-white/10 p-5 text-sm text-white/90 backdrop-blur rise">
            <div className="mb-3 flex items-center gap-2 font-semibold">
              <span className="live-dot h-2 w-2 rounded-full bg-flex-green" /> Simulation Mode
            </div>
            {!user ? (
              <form
                className="space-y-3"
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    setError("");
                    await login(email, password);
                  } catch (err) {
                    setError(String(err));
                  }
                }}
              >
                <label className="block">
                  <span className="text-xs text-white/60">Email</span>
                  <input
                    className="mt-1 w-full rounded-xl border border-white/20 bg-black/20 px-3 py-2"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-white/60">Password</span>
                  <input
                    type="password"
                    className="mt-1 w-full rounded-xl border border-white/20 bg-black/20 px-3 py-2"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </label>
                {error ? <p className="text-flex-orange">{error}</p> : null}
                <button type="submit" className="btn-accent w-full">
                  Sign in
                </button>
                <p className="text-xs text-white/55">
                  Demo: consumer / aggregator / utility / admin @gridflex.pk · demo1234
                </p>
              </form>
            ) : (
              <p>
                Signed in as <strong>{user.full_name}</strong> ({user.role}). Explore dashboards above.
              </p>
            )}
          </div>
        </div>
      </section>

      {status ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Stat label="Current demand" value={`${status.current_demand_mw} MW`} tone="blue" />
          <Stat label="Available flexibility" value={`${status.available_flexibility_mw} MW`} tone="green" />
          <Stat label="Peak demand" value={`${status.peak_demand_mw} MW`} tone="orange" />
          <Stat label="Renewable generation" value={`${status.renewable_generation_mw} MW`} tone="orange" />
          <Stat label="Battery capacity" value={`${status.battery_capacity_mwh} MWh`} tone="purple" />
          <Stat label="Active DR events" value={status.active_dr_events} tone="red" />
        </section>
      ) : null}

      {concept ? (
        <section className="panel p-6">
          <h2 className="font-display text-2xl font-semibold">{concept.title}</h2>
          <p className="mt-1 text-flex-ink/65">{concept.subtitle}</p>
          <ol className="mt-4 grid gap-2 md:grid-cols-2">
            {concept.steps.map((s: string, i: number) => (
              <li key={s} className="rounded-xl bg-flex-mist/80 px-4 py-3 text-sm">
                <span className="mr-2 font-display font-semibold text-flex-blue">{i + 1}.</span>
                {s}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </div>
  );
}