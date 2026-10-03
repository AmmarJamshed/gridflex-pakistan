import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function RegulatoryPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.regulatory().then(setData).catch(console.error);
  }, []);

  if (!data) return <p>Loading regulatory compatibility…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold">Pakistan Regulatory Compatibility</h1>
        <p className="mt-2 max-w-3xl rounded-xl bg-flex-orange/10 px-4 py-3 text-sm text-flex-orange">
          {data.disclaimer}
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel p-5">
          <h2 className="font-display text-xl font-semibold">Current regulatory facts</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-flex-ink/80">
            {data.current_regulatory_facts.map((x: string) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </section>
        <section className="panel p-5">
          <h2 className="font-display text-xl font-semibold">Proposed future model</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-flex-ink/80">
            {data.proposed_future_model.map((x: string) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="panel p-5">
        <h2 className="font-display text-xl font-semibold">Areas requiring approval / review</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {data.areas_requiring_approval_or_review.map((x: string) => (
            <span key={x} className="rounded-full bg-flex-mist px-3 py-1.5 text-sm">
              {x}
            </span>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {data.institutions.map((x: string) => (
            <span key={x} className="chip bg-flex-blue/15 text-flex-blue">
              {x}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}