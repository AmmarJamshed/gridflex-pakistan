import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import Stat from "../components/Stat";
import ConditionChip from "../components/ConditionChip";

export default function MarketPage() {
  const { login } = useAuth();
  const [summary, setSummary] = useState<any>(null);
  const [offers, setOffers] = useState<any[]>([]);
  const [bids, setBids] = useState<any[]>([]);
  const [txs, setTxs] = useState<any[]>([]);
  const [clearResult, setClearResult] = useState<any>(null);
  const [example, setExample] = useState<any>(null);
  const [prices, setPrices] = useState<any[]>([]);

  async function refresh() {
    const [s, o, b, t, ex, p] = await Promise.all([
      api.marketSummary(),
      api.offers(),
      api.bids(),
      api.transactions(),
      api.clearingExample(),
      api.prices(),
    ]);
    setSummary(s);
    setOffers(o);
    setBids(b);
    setTxs(t);
    setExample(ex);
    setPrices(p);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  async function clearMarket() {
    await login("utility@gridflex.pk", "demo1234");
    const token = localStorage.getItem("gf_token");
    if (!token) return;
    const result = await api.clearMarket(token);
    setClearResult(result);
    await refresh();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold">Flexibility marketplace</h1>
          <p className="text-flex-ink/65">Zone-constrained matching · prototype prices in PKR/kWh.</p>
        </div>
        <button type="button" className="btn-accent" onClick={clearMarket}>
          Run market clearing
        </button>
      </div>

      {summary ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label="Active offers" value={summary.active_offers} tone="green" />
          <Stat label="Active bids" value={summary.active_bids} tone="blue" />
          <Stat label="Cleared txs" value={summary.cleared_transactions} tone="purple" />
          <Stat label="Flex price" value={`PKR ${summary.current_flexibility_price}`} tone="orange" />
          <Stat label="Traded energy" value={`${summary.total_traded_energy_kwh} kWh`} tone="purple" />
        </div>
      ) : null}

      {clearResult ? (
        <div className="panel border-l-4 border-l-flex-purple p-4 text-sm">
          Cleared <strong>{clearResult.cleared_volume_kw} kW</strong> ·{" "}
          <strong>{clearResult.transaction_count}</strong> txs · clearing price{" "}
          <strong>PKR {clearResult.clearing_price ?? "—"}</strong> · seller revenue{" "}
          <strong>PKR {clearResult.total_seller_revenue_pkr}</strong>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="panel overflow-hidden">
          <div className="border-b border-black/5 px-4 py-3 font-display font-semibold">Sell offers</div>
          <div className="max-h-80 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-flex-mist/70 text-xs uppercase text-flex-ink/50">
                <tr>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">kW</th>
                  <th className="px-3 py-2">Min PKR</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {offers.map((o) => (
                  <tr key={o.id} className="border-t border-black/5">
                    <td className="px-3 py-2">{o.flexibility_type}</td>
                    <td className="px-3 py-2">{o.remaining_kw}/{o.power_kw}</td>
                    <td className="px-3 py-2">{o.min_price_pkr_per_kwh}</td>
                    <td className="px-3 py-2"><ConditionChip condition={o.status === "open" ? "green" : "peak"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel overflow-hidden">
          <div className="border-b border-black/5 px-4 py-3 font-display font-semibold">Buy bids</div>
          <div className="max-h-80 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-flex-mist/70 text-xs uppercase text-flex-ink/50">
                <tr>
                  <th className="px-3 py-2">Need kW</th>
                  <th className="px-3 py-2">Max PKR</th>
                  <th className="px-3 py-2">Urgency</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {bids.map((b) => (
                  <tr key={b.id} className="border-t border-black/5">
                    <td className="px-3 py-2">{b.remaining_kw}/{b.power_kw}</td>
                    <td className="px-3 py-2">{b.max_price_pkr_per_kwh}</td>
                    <td className="px-3 py-2">{b.urgency}</td>
                    <td className="px-3 py-2">{b.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="panel p-4">
        <h2 className="font-display text-xl font-semibold">Cleared transactions</h2>
        <div className="mt-3 max-h-64 overflow-auto text-sm">
          {txs.length === 0 ? (
            <p className="text-flex-ink/55">No cleared transactions yet — run market clearing.</p>
          ) : (
            <table className="w-full text-left">
              <thead className="text-xs uppercase text-flex-ink/50">
                <tr>
                  <th className="py-2">ID</th>
                  <th>kW</th>
                  <th>kWh</th>
                  <th>Clear PKR</th>
                  <th>Seller net</th>
                  <th>Hash</th>
                </tr>
              </thead>
              <tbody>
                {txs.map((t) => (
                  <tr key={t.id} className="border-t border-black/5">
                    <td className="py-2 font-mono text-xs">{t.id.slice(0, 8)}</td>
                    <td>{t.power_kw}</td>
                    <td>{t.energy_kwh}</td>
                    <td>{t.clearing_price}</td>
                    <td className="text-flex-purple">{t.seller_revenue_pkr}</td>
                    <td className="font-mono text-[10px] text-flex-ink/45">{t.blockchain_hash?.slice(0, 12)}…</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {example ? (
          <div className="panel p-4 text-sm">
            <h3 className="font-display text-lg font-semibold">Clearing example (400 kW @ max PKR 12)</h3>
            <p className="mt-2">
              Cleared {example.cleared_volume_kw} kW at PKR {example.clearing_price}/kWh · buyer cost PKR{" "}
              {example.buyer_cost_pkr} · seller revenue PKR {example.seller_revenue_pkr}
            </p>
          </div>
        ) : null}
        <div className="panel p-4 text-sm">
          <h3 className="font-display text-lg font-semibold">Dynamic prices (simulated)</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {prices.filter((p) => [8, 13, 19, 21].includes(p.hour)).map((p) => (
              <span key={p.hour} className="rounded-lg bg-flex-mist px-3 py-2">
                {p.hour}:00 · PKR {p.price_pkr_per_kwh} · {p.condition}
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs text-flex-ink/50">Prototype/simulated — not official tariffs.</p>
        </div>
      </div>
    </div>
  );
}