import React from "react";
import { LayoutDashboard, Award, FileSpreadsheet } from "lucide-react";

export type NavTab = "dashboard" | "create" | "templates";

interface AppShellProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  children: React.ReactNode;
  pageTitle: string;
}

export function AppShell({ activeTab, setActiveTab, children, pageTitle }: AppShellProps) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "create", label: "Create Presentation", icon: Award },
    { id: "templates", label: "Templates", icon: FileSpreadsheet },
  ];

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      {/* Sidebar */}
      <aside className="hidden md:flex fixed inset-y-0 left-0 z-20 w-64 flex-col border-r border-border bg-sidebar">
        {/* Brand Header */}
        <div className="flex h-16 items-center px-6 border-b border-sidebar-border gap-3">
          <div className="flex h-9 items-center justify-center rounded-md bg-primary px-3 shadow-xs">
            <span className="text-primary-foreground font-bold tracking-tight text-lg leading-none">
              KONE
            </span>
          </div>
          <span className="font-semibold text-sm tracking-tight text-foreground/90">
            Recognition Studio
          </span>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as NavTab)}
                className={`w-full flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors text-left ${
                  isActive
                    ? "bg-sidebar-accent text-primary font-semibold shadow-xs"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground cursor-pointer"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                <span className="flex-1">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Container */}
      <div className="flex-1 md:pl-64 flex flex-col min-w-0">
        {/* Header */}
        <header className="sticky top-0 z-10 h-16 border-b border-border bg-background/80 backdrop-blur flex items-center px-6 justify-between">
          <div className="flex items-center gap-3">
            <div className="md:hidden flex items-center gap-2">
              <div className="flex h-8 items-center justify-center rounded bg-primary px-2">
                <span className="text-primary-foreground font-bold text-sm">KONE</span>
              </div>
            </div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">{pageTitle}</h1>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 min-w-0">
          <div className="mx-auto w-full max-w-7xl px-6 py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
