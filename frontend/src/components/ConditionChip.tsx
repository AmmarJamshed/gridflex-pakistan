export default function ConditionChip({ condition }: { condition: string }) {
  const map: Record<string, string> = {
    normal: "bg-flex-blue/15 text-flex-blue",
    peak: "bg-flex-orange/15 text-flex-orange",
    critical: "bg-flex-red/15 text-flex-red",
    green: "bg-flex-green/15 text-flex-green",
  };
  return <span className={`chip ${map[condition] ?? map.normal}`}>{condition}</span>;
}