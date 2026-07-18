"use client";

import { Shield } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-border/50 py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <span className="text-sm font-semibold">SentinelRAG</span>
          </div>

          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} SentinelRAG. All rights reserved.
          </p>

          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#" className="transition-colors hover:text-foreground">
              Documentation
            </a>
            <a href="#" className="transition-colors hover:text-foreground">
              GitHub
            </a>
            <a href="#" className="transition-colors hover:text-foreground">
              Contact
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
