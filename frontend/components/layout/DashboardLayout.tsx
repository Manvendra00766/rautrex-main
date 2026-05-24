import { Sidebar } from "./Sidebar";
import { Navbar } from "./Navbar";
interface DashboardLayoutProps {
  children: React.ReactNode;
}
export default function DashboardLayout({ 
  children 
}: DashboardLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden 
      bg-[var(--bg-base)]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 
        overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto 
          custom-scrollbar
          p-4 md:p-6 
          space-y-6
          bg-[var(--bg-base)]">
          {children}
        </main>
      </div>
    </div>
  );
}
