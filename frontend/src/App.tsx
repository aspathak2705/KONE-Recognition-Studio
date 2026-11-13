import { useState } from "react";
import { AppShell, NavTab } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { CreatePresentation } from "./pages/CreatePresentation";

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");

  const pageTitles: Record<NavTab, string> = {
    dashboard: "Dashboard",
    create: "Create Presentation",
  };

  return (
    <AppShell
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      pageTitle={pageTitles[activeTab]}
    >
      {activeTab === "dashboard" && (
        <Dashboard
          onNavigateToCreate={() => setActiveTab("create")}
        />
      )}
      {activeTab === "create" && (
        <CreatePresentation />
      )}
    </AppShell>
  );
}

export default App;
