export default function DashboardLoading() {
  return (
    <div className="flex flex-col gap-6 p-8 animate-pulse">
      <div className="h-8 w-48 bg-muted rounded"></div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="h-32 bg-card rounded-xl border border-border"></div>
        <div className="h-32 bg-card rounded-xl border border-border"></div>
        <div className="h-32 bg-card rounded-xl border border-border"></div>
      </div>
      <div className="h-[400px] w-full bg-card rounded-xl border border-border"></div>
    </div>
  )
}
