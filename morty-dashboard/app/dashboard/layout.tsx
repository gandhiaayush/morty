import Sidebar from "@/components/layout/Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="ml-[220px] flex-1 flex flex-col min-h-full bg-zinc-950 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
