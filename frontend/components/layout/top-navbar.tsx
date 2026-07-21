"use client";

import { usePathname } from "next/navigation";
import { ChevronRight, Bell, Search, Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

const breadcrumbMap: Record<string, string> = {
  dashboard: "Overview",
  upload: "Upload",
  chat: "Chat",
  documents: "Documents",
  search: "Search",
  evaluation: "Evaluation",
  settings: "Settings",
};

export function TopNavbar({ onMenuClick }: { onMenuClick?: () => void }) {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background/80 backdrop-blur-xl px-4 sm:px-6">
      <div className="flex items-center gap-2 text-sm">
        <button
          onClick={onMenuClick}
          className="rounded-lg p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
        {segments.map((seg, i) => (
          <span key={seg} className="flex items-center gap-2">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
            <span
              className={cn(
                i === segments.length - 1
                  ? "font-medium text-foreground"
                  : "text-muted-foreground hidden sm:inline"
              )}
            >
              {breadcrumbMap[seg] || seg}
            </span>
          </span>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button variant="ghost" size="icon" className="hidden sm:flex">
          <Search className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="hidden sm:flex">
          <Bell className="h-4 w-4" />
        </Button>
        <div className="ml-2 flex items-center gap-2 border-l pl-3">
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
