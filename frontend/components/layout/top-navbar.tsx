"use client";

import { usePathname } from "next/navigation";
import { ChevronRight, Bell, Search } from "lucide-react";
import { cn } from "@/lib/utils";

const breadcrumbMap: Record<string, string> = {
  dashboard: "Dashboard",
  upload: "Upload",
  chat: "Chat",
  documents: "Documents",
  evaluation: "Evaluation",
  settings: "Settings",
};

export function TopNavbar() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/80 backdrop-blur-xl px-6">
      <div className="flex items-center gap-2 text-sm">
        {segments.map((seg, i) => (
          <span key={seg} className="flex items-center gap-2">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
            <span className={cn(i === segments.length - 1 ? "font-medium text-foreground" : "text-muted-foreground")}>
              {breadcrumbMap[seg] || seg}
            </span>
          </span>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <button className="rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors">
          <Search className="h-4 w-4" />
        </button>
        <button className="relative rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors">
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary" />
        </button>
        <div className="ml-2 flex items-center gap-2 border-l border-border pl-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
            SO
          </div>
          <div className="hidden sm:block">
            <p className="text-xs font-medium">Operator</p>
            <p className="text-[10px] text-muted-foreground">admin</p>
          </div>
        </div>
      </div>
    </header>
  );
}
