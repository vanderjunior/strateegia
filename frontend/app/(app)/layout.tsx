import type { PropsWithChildren } from "react";

import { AppShell } from "@/components/layout/AppShell";

export default function DashboardLayout({ children }: PropsWithChildren) {
  return <AppShell>{children}</AppShell>;
}
