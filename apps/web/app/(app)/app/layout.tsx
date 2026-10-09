import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { auth, signOut } from "@/auth";
import { AppShell } from "@/components/shell/AppShell";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const session = await auth();
  if (!session?.user) redirect("/login");

  async function doSignOut() {
    "use server";
    await signOut({ redirectTo: "/login" });
  }

  return (
    <AppShell
      user={{ name: session.user.name ?? "User", role: session.user.role }}
      signOut={doSignOut}
      breadcrumb={<span className="text-ink">Worklist</span>}
    >
      {children}
    </AppShell>
  );
}
