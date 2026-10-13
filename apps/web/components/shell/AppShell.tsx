import type { ReactNode } from "react";
import { RailNav } from "./RailNav";
import { TopBar, type TopBarUser } from "./TopBar";

export function AppShell({
  user,
  signOut,
  breadcrumb,
  children,
}: {
  user: TopBarUser;
  signOut: () => Promise<void>;
  breadcrumb: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex h-dvh overflow-hidden bg-paper text-ink">
      <RailNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar breadcrumb={breadcrumb} user={user} signOut={signOut} />
        <main id="main" className="min-h-0 flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
