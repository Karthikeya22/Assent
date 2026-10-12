import { LatticePoster } from "@/components/lattice/LatticePoster";
import { Architecture } from "@/components/marketing/Architecture";
import { Benchmark } from "@/components/marketing/Benchmark";
import { Closing } from "@/components/marketing/Closing";
import { GlassBox } from "@/components/marketing/GlassBox";
import { Hero } from "@/components/marketing/Hero";
import { Ledger } from "@/components/marketing/Ledger";
import { Standards } from "@/components/marketing/Standards";
import { Story } from "@/components/marketing/Story";
import { TwoAgents } from "@/components/marketing/TwoAgents";

export default function Home() {
  return (
    <main>
      <Hero />
      <Ledger />
      <Story poster={<LatticePoster title="The criteria graph after review: proven criteria in green, one downgraded to insufficient." />} />
      <GlassBox />
      <TwoAgents />
      <Standards />
      <Benchmark />
      <Architecture />
      <Closing />
    </main>
  );
}
