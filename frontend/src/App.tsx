import { useState } from "react";
import { AppShell, NavTab } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { ExcelImport } from "./pages/ExcelImport";
import { TemplateManager } from "./pages/TemplateManager";
import { RecognitionProjects } from "./pages/RecognitionProjects";

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");

  const pageTitles: Record<NavTab, string> = {
    dashboard: "Dashboard",
    import: "Excel Import",
    templates: "Template Inspector",
    projects: "Recognition Projects",
    settings: "Settings",
  };

  return (
    <AppShell
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      pageTitle={pageTitles[activeTab]}
    >
      {activeTab === "dashboard" && (
        <Dashboard
          onNavigateToImport={() => setActiveTab("import")}
          onNavigateToTemplates={() => setActiveTab("templates")}
        />
      )}
      {activeTab === "import" && <ExcelImport />}
      {activeTab === "templates" && <TemplateManager />}
      {activeTab === "projects" && <RecognitionProjects />}
    </AppShell>
  );
}

export default App;
