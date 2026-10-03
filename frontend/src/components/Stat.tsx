type Props = {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "green" | "blue" | "orange" | "red" | "purple";
};

const tones = {
  green: "border-l-flex-green",
  blue: "border-l-flex-blue",
  orange: "border-l-flex-orange",
  red: "border-l-flex-red",
  purple: "border-l-flex-purple",
};

export default function Stat({ label, value, hint, tone = "blue" }: Props) {
  return (
    <div className={`stat border-l-4 ${tones[tone]} rise`}>
      <div className="text-xs font-medium uppercase tracking-wide text-flex-ink/55">{label}</div>
      <div className="mt-1 font-display text-2xl font-semibold">{value}</div>
      {hint ? <div className="mt-1 text-xs text-flex-ink/55">{hint}</div> : null}
    </div>
  );
}