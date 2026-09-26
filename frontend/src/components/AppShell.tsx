import React from "react";
import { LayoutDashboard, Award, FileSpreadsheet, Settings, FileUp } from "lucide-react";

export type NavTab = "dashboard" | "import" | "templates" | "generate" | "projects" | "settings";

interface AppShellProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  children: React.ReactNode;
  pageTitle: string;
}

export function AppShell({ activeTab, setActiveTab, children, pageTitle }: AppShellProps) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, disabled: false },
    { id: "import", label: "Excel Import", icon: FileUp, disabled: false },
    { id: "templates", label: "Templates", icon: FileSpreadsheet, disabled: false },
    { id: "generate", label: "Generate Presentation", icon: Award, disabled: false },
    { id: "projects", label: "Recognition Projects", icon: Award, disabled: false },
    { id: "settings", label: "Settings (Phase 3)", icon: Settings, disabled: true },
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
                onClick={() => !item.disabled && setActiveTab(item.id as NavTab)}
                disabled={item.disabled}
                className={`w-full flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors text-left ${
                  isActive
                    ? "bg-sidebar-accent text-primary font-semibold shadow-xs"
                    : item.disabled
                    ? "text-muted-foreground/50 cursor-not-allowed"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground cursor-pointer"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                <span className="flex-1">{item.label}</span>
                {item.disabled && (
                  <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                    Soon
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Scope Note */}
        <div className="p-4 border-t border-sidebar-border">
          <div className="p-3 rounded-md bg-muted/60 text-xs text-muted-foreground space-y-1">
            <p className="font-medium text-foreground">Phase 1 — Data & Templates</p>
            <p>Excel validation & PowerPoint inspection active.</p>
          </div>
        </div>
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

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
              Phase 1 Active
            </span>
            <div className="h-8 w-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
              HR
            </div>
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
