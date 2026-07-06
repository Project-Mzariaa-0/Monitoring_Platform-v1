"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/live", label: "Live View" },
  { href: "/logs", label: "Audit Log" },
  { href: "/equipment", label: "Equipment" },
  { href: "/analytics", label: "Analytics" },
  { href: "/scheduler", label: "Scheduler" },
  { href: "/settings", label: "Settings" },
];

function pageTitle(pathname: string) {
  if (pathname === "/") return "Supervisor Overview";
  if (pathname.startsWith("/live")) return "Live View";
  if (pathname.startsWith("/logs")) return "Unit Logs";
  if (pathname.startsWith("/equipment")) return "Equipment";
  if (pathname.startsWith("/analytics")) return "Analytics";
  if (pathname.startsWith("/scheduler/new")) return "Schedule New Session";
  if (pathname.startsWith("/scheduler")) return "Scheduler";
  if (pathname.startsWith("/sessions")) return "Session Detail";
  if (pathname.startsWith("/settings/patient")) return "Patient/Herd Settings";
  if (pathname.startsWith("/settings")) return "Settings";
  return "Milking Monitor";
}

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: session } = useSession();
  const user = session?.user;
  const name = user?.name || user?.email || "Guest";
  const initials = user?.name
    ? user.name.split(" ").map((n) => n[0]).join("").substring(0, 2).toUpperCase()
    : user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "??";
  const showEmergency = pathname.startsWith("/live") || pathname.startsWith("/analytics");

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <Link href="/" className="brand" aria-label="Milking Monitor dashboard">
          <img src="/logo12.png" alt="Milking Monitor" className="brand-logo brand-logo-sidebar" />
        </Link>

        <span className="small-muted" style={{ paddingLeft: 8 }}>Dashboard</span>
        <nav className="side-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href} className={isActive(pathname, item.href) ? "active" : undefined}>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <Link className="sidebar-action" href="/scheduler/new">
          New Session
        </Link>

        <div className="sidebar-spacer" />

        <div className="profile-card" style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="avatar">{initials}</span>
          <span style={{ flex: 1, minWidth: 0 }}>
            <span style={{ display: "block", color: "#fff", fontWeight: 750, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={name}>
              {name}
            </span>
            <span className="small-muted" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>Supervisor</span>
              <button
                onClick={() => signOut({ callbackUrl: "/sign-in" })}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#E4E0D2",
                  cursor: "pointer",
                  fontSize: "11px",
                  padding: "0",
                  textDecoration: "underline"
                }}
              >
                Sign out
              </button>
            </span>
          </span>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div>
            <h1 className="page-title">{pageTitle(pathname)}</h1>
            <div className="small-muted" style={{ marginTop: 6 }}>
              Cooperative Dairy Unit
            </div>
          </div>
          <div className="topbar-tools">
            <input className="search" aria-label="Global search" placeholder="Search cow ID, operator, task" />
            <button className="icon-button" title="Notifications" aria-label="Notifications">
              N
            </button>
            <button className="icon-button" title="Alerts" aria-label="Alerts">
              !
            </button>
            <button className="icon-button" title="Help" aria-label="Help">
              ?
            </button>
            {showEmergency ? <button className="button button-danger">Emergency Stop</button> : null}
          </div>
        </header>
        <main className="page">{children}</main>
      </div>
    </div>
  );
}
