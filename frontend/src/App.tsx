import { useState } from "react";
import { AppShell, NavTab } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { CreatePresentation } from "./pages/CreatePresentation";
import { TemplateLibrary } from "./pages/TemplateLibrary";

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");

  const pageTitles: Record<NavTab, string> = {
    dashboard: "Dashboard",
    create: "Create Presentation",
    templates: "Template Library",
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
          onNavigateToTemplates={() => setActiveTab("templates")}
        />
      )}
      {activeTab === "create" && (
        <CreatePresentation
          onNavigateToTemplates={() => setActiveTab("templates")}
        />
      )}
      {activeTab === "templates" && <TemplateLibrary />}
    </AppShell>
  );
}

export default App;
