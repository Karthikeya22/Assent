import { Footer } from "@/components/marketing/Footer";
import { Nav } from "@/components/marketing/Nav";
import { ScrollDriver } from "@/components/world/ScrollDriver";

/** Marketing pages: light only (DESIGN.md), Lenis smooth scroll, paper grain. Never used by the app. */
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-light grain min-h-dvh">
      <ScrollDriver />
      <Nav />
      {children}
      <Footer />
    </div>
  );
}
