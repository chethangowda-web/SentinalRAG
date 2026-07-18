"use client";

import { Sidebar } from "./sidebar";
import { TopNavbar } from "./top-navbar";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="ml-64 flex flex-1 flex-col">
        <TopNavbar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
