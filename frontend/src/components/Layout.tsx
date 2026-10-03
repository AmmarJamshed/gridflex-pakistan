import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";

const links = [
  { to: "/", label: "Home" },
  { to: "/simulation", label: "Simulation" },
  { to: "/consumer", label: "Consumer" },
  { to: "/aggregator", label: "Aggregator" },
  { to: "/market", label: "Market" },
  { to: "/grid", label: "Grid" },
  { to: "/admin", label: "Admin" },
  { to: "/regulatory", label: "Regulatory" },
];

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-white/50 bg-[#0e1a24]/92 text-white backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-flex-green to-flex-blue font-display text-sm font-bold">
              GF
            </div>
            <div>
              <div className="font-display text-lg font-semibold tracking-tight">GRIDFLEX Pakistan</div>
              <div className="text-xs text-white/70">Turn unused electricity flexibility into value.</div>
            </div>
          </div>
          <nav className="flex flex-wrap gap-1">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === "/"}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm ${
                    isActive ? "bg-white/15 text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="text-sm text-white/80">
            {user ? (
              <button type="button" onClick={logout} className="rounded-lg bg-white/10 px-3 py-1.5 hover:bg-white/20">
                {user.full_name} · logout
              </button>
            ) : (
              <span className="text-white/60">Demo mode</span>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-black/5 px-4 py-6 text-center text-xs text-flex-ink/60">
        Research/prototype · Simulated prices · Illustrative grid model — not an operational Pakistani electricity market.
      </footer>
    </div>
  );
}