import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type HourPoint = {
  hour: number;
  demand_mw: number;
  generation_mw: number;
  solar_mw: number;
  battery_mw: number;
  flexible_demand_mw: number;
  cleared_volume_mw: number;
  price_pkr: number;
  grid_condition: string;
};

type Props = {
  without?: HourPoint[];
  withFlex?: HourPoint[];
  peakThreshold?: number;
  mode?: "compare" | "with" | "without";
};

export default function HourlyChart({ without, withFlex, peakThreshold, mode = "compare" }: Props) {
  const [selected, setSelected] = useState<number | null>(null);

  const data = useMemo(() => {
    const base = withFlex ?? without ?? [];
    return base.map((p, i) => ({
      hour: p.hour,
      demand_with: withFlex?.[i]?.demand_mw,
      demand_without: without?.[i]?.demand_mw,
      generation: p.generation_mw,
      solar: p.solar_mw,
      battery: p.battery_mw,
      flexible: p.flexible_demand_mw,
      cleared: withFlex?.[i]?.cleared_volume_mw ?? p.cleared_volume_mw,
      price: withFlex?.[i]?.price_pkr ?? p.price_pkr,
      condition: withFlex?.[i]?.grid_condition ?? p.grid_condition,
    }));
  }, [without, withFlex]);

  const detail = selected != null ? data[selected] : null;

  return (
    <div className="panel p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h3 className="font-display text-lg font-semibold">24-hour electricity profile</h3>
          <p className="text-sm text-flex-ink/60">Click a point to inspect hour details (MW / PKR prototype).</p>
        </div>
        <span className="live-dot inline-block h-2.5 w-2.5 rounded-full bg-flex-green" />
      </div>
      <div className="h-[360px] w-full">
        <ResponsiveContainer>
          <LineChart
            data={data}
            onClick={(state) => {
              const idx = (state as any)?.activeTooltipIndex;
              if (typeof idx === "number") setSelected(idx);
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#c5d5ce" />
            <XAxis dataKey="hour" tickFormatter={(h) => `${h}:00`} />
            <YAxis unit=" MW" />
            <Tooltip />
            <Legend />
            {peakThreshold ? (
              <ReferenceLine y={peakThreshold} stroke="#c0392b" strokeDasharray="4 4" label="Peak threshold" />
            ) : null}
            {(mode === "compare" || mode === "without") && without ? (
              <Line type="monotone" dataKey="demand_without" name="Demand (without)" stroke="#c0392b" strokeWidth={2} dot={false} />
            ) : null}
            {(mode === "compare" || mode === "with") && withFlex ? (
              <Line type="monotone" dataKey="demand_with" name="Demand (with GRIDFLEX)" stroke="#1b6ca8" strokeWidth={2.5} dot={false} />
            ) : null}
            <Line type="monotone" dataKey="solar" name="Solar" stroke="#e08a2b" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="flexible" name="Flexible demand" stroke="#1fa97a" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="battery" name="Battery" stroke="#6c4ab6" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="cleared" name="Cleared volume" stroke="#6c4ab6" strokeDasharray="5 3" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {detail ? (
        <div className="mt-4 grid gap-3 rounded-xl bg-flex-mist/80 p-4 sm:grid-cols-5">
          <div><div className="text-xs text-flex-ink/55">Hour</div><div className="font-semibold">{detail.hour}:00</div></div>
          <div><div className="text-xs text-flex-ink/55">Demand</div><div className="font-semibold">{detail.demand_with ?? detail.demand_without} MW</div></div>
          <div><div className="text-xs text-flex-ink/55">Flexibility</div><div className="font-semibold text-flex-green">{detail.flexible} MW</div></div>
          <div><div className="text-xs text-flex-ink/55">Cleared</div><div className="font-semibold text-flex-purple">{detail.cleared} MW</div></div>
          <div><div className="text-xs text-flex-ink/55">Price / condition</div><div className="font-semibold">PKR {detail.price} · {detail.condition}</div></div>
        </div>
      ) : null}
    </div>
  );
}