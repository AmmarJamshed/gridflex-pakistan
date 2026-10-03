import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import Stat from "../components/Stat";

export default function AggregatorPage() {
  const { login } = useAuth();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    (async () => {
      await login("aggregator@gridflex.pk", "demo1234");
      const t = localStorage.getItem("gf_token");
      if (t) setData(await api.aggregatorDashboard(t));
    })().catch(console.error);
  }, [login]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold">Aggregator dashboard</h1>
        <p className="text-flex-ink/65">
          Thousands of small consumers become one virtual flexibility resource.
        </p>
      </div>
      {data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Pooled households" value={data.pooled_households.toLocaleString()} tone="blue" />
            <Stat label="Per-home flexibility" value={`${data.flexibility_per_household_kw} kW`} tone="green" />
            <Stat label="Aggregated flexibility" value={`${data.aggregated_flexibility_mw} MW`} tone="purple" />
            <Stat label="Active offers" value={data.active_offers} tone="orange" />
          </div>
          <div className="panel relative overflow-hidden p-6">
            <div className="absolute -right-8 -top-8 h-40 w-40 rounded-full bg-flex-purple/15" />
            <h2 className="font-display text-xl font-semibold">Virtual power resource</h2>
            <p className="mt-3 max-w-2xl text-lg">{data.narrative}</p>
            <p className="mt-4 text-sm text-flex-ink/60">
              Physical delivery remains on DISCO feeders. The aggregator coordinates verified
              behavioral / DER flexibility and settles value in the marketplace.
            </p>
          </div>
        </>
      ) : (
        <p>Loading aggregator pool…</p>
      )}
    </div>
  );
}