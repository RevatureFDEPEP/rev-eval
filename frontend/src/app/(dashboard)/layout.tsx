import type { ReactNode } from "react";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { AuthProvider } from "@/lib/auth/AuthContext";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <DashboardShell>{children}</DashboardShell>
    </AuthProvider>
  );
}
