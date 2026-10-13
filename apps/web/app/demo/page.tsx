import type { Metadata } from "next";
import { DemoWorkspace, type DemoBundle } from "@/components/demo/DemoWorkspace";
import { Nav } from "@/components/marketing/Nav";
import demo from "@/content/demo.json";

export const metadata: Metadata = {
  title: "Live demo",
  description: "Watch Assent prove a Medicare coverage policy on a synthetic chart, criterion by criterion.",
};

// No login: a real recorded run replays through the same workspace components the app uses.
export default function DemoPage() {
  return (
    // Public page: light only, like the rest of the marketing site (DESIGN.md).
    <div className="theme-light min-h-dvh">
      <Nav />
      <DemoWorkspace demo={demo as unknown as DemoBundle} />
    </div>
  );
}
