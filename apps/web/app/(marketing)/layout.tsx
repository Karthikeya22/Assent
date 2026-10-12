import { Footer } from "@/components/marketing/Footer";
import { Nav } from "@/components/marketing/Nav";
import { SmoothScroll } from "@/components/marketing/SmoothScroll";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SmoothScroll />
      <Nav />
      {children}
      <Footer />
    </>
  );
}
