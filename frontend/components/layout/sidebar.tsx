"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Upload,
  MessageSquare,
  Files,
  BarChart3,
  Settings,
  Shield,
  GitBranch,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/upload", label: "Upload", icon: Upload },
  { href: "/dashboard/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard/documents", label: "Documents", icon: Files },
  { href: "/dashboard/explainability", label: "Explainability", icon: GitBranch },
  { href: "/dashboard/evaluation", label: "Evaluation", icon: BarChart3 },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-border bg-background">
      <div className="flex h-16 items-center gap-2 border-b border-border px-6">
        <Shield className="h-6 w-6 text-primary" />
        <span className="text-lg font-bold tracking-tight">SentinelRAG</span>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}>
              <div
                className={cn(
                  "relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute inset-0 rounded-lg bg-primary/10"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <Icon className="relative z-10 h-5 w-5" />
                <span className="relative z-10">{item.label}</span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4">
        <div className="rounded-lg bg-secondary/50 p-3">
          <p className="text-xs font-medium text-foreground">RAG Pipeline</p>
          <p className="mt-1 text-[10px] text-muted-foreground">Self-Correcting · v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}
