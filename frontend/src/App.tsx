import { useState } from "react";
import { AppShell, NavTab } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { RecognitionProjects } from "./pages/RecognitionProjects";

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");

  const pageTitles: Record<NavTab, string> = {
    dashboard: "Dashboard",
    projects: "Recognition Projects",
    templates: "Templates",
    settings: "Settings",
  };

  return (
    <AppShell
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      pageTitle={pageTitles[activeTab]}
    >
      {activeTab === "dashboard" && (
        <Dashboard onNavigateToProjects={() => setActiveTab("projects")} />
      )}
      {activeTab === "projects" && <RecognitionProjects />}
    </AppShell>
  );
}

export default App;
