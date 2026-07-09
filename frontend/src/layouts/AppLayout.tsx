import { NavLink, Outlet } from "react-router-dom";
import { BarChart3, LayoutDashboard, List, Settings, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "数据概览", icon: BarChart3, end: true },
  { to: "/quota", label: "账号额度", icon: LayoutDashboard },
  { to: "/usage-all", label: "调用日志", icon: List },
  { to: "/accounts", label: "账号管理", icon: Users },
  { to: "/settings", label: "设置", icon: Settings },
];

export function AppLayout() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-6 md:px-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="h-10 w-10 shrink-0" aria-hidden />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-800">QuotaHub</h1>
          </div>
        </div>
        <nav className="flex items-center gap-1 rounded-xl bg-slate-100 p-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                  isActive ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
