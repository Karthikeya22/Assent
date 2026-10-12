import { POLICY, layout } from "./layout";
import { heroFrame, ringFill } from "./timeline";

/** Static SVG of the lattice (server-rendered): the LCP image, the reduced-motion view, the no-GPU view. */
export function LatticePoster({ title }: { title: string }) {
  const nodes = layout();
  const f = heroFrame(nodes, 0.7); // a still mid-loop: one criterion proven, one insufficient
  const byKey = new Map(nodes.map((n) => [n.key, n]));
  // Simple orthographic projection of the 3D layout into a 640x520 box.
  const X = (x: number) => (x + 3.0) * 100;
  const Y = (y: number) => (2.2 - y) * 100;
  const color = (k: string) =>
    f.leaves[k] === "met" ? "var(--signal)" : f.leaves[k] === "amber" ? "var(--gap)" : "var(--ink-3)";
  return (
    <svg viewBox="0 0 640 520" role="img" aria-label={title} className="h-full w-full">
      <title>{title}</title>
      {Array.from({ length: 12 }, (_, i) => (
        <g key={i} transform={`translate(${40 + i * 4} ${150 - i * 3}) skewY(-6)`} opacity={0.35 + i * 0.05}>
          <rect width="78" height="104" rx="2" fill="var(--paper-raised)" stroke="var(--rule)" />
          {Array.from({ length: 11 }, (_, r) => (
            <rect key={r} x="8" y={10 + r * 8.5} width={24 + ((r * 37 + i * 11) % 38)} height="2.4" fill={i === 11 && r === 6 ? "var(--signal)" : "var(--ink-3)"} opacity={i === 11 && r === 6 ? 1 : 0.55} />
          ))}
        </g>
      ))}
      {nodes
        .filter((n) => n.parent)
        .map((n) => {
          const p = byKey.get(n.parent!)!;
          return <line key={n.key} x1={X(p.pos[0])} y1={Y(p.pos[1])} x2={X(n.pos[0])} y2={Y(n.pos[1])} stroke="var(--ink-3)" strokeOpacity="0.45" strokeWidth="1" />;
        })}
      {nodes.map((n) => {
        const cx = X(n.pos[0]);
        const cy = Y(n.pos[1]);
        if (n.kind === "LEAF") {
          const wire = f.leaves[n.key] === "wire";
          return <circle key={n.key} cx={cx} cy={cy} r="7" fill={wire ? "none" : color(n.key)} stroke={color(n.key)} strokeWidth="1.2" />;
        }
        const r = n.parent === null ? 20 : 12;
        const fill = ringFill(nodes, f.leaves, n.key);
        const c = 2 * Math.PI * r;
        return (
          <g key={n.key}>
            <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--ink-3)" strokeOpacity="0.35" strokeWidth="1.5" />
            <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--signal)" strokeWidth="2.5" strokeDasharray={`${c * fill} ${c}`} transform={`rotate(-90 ${cx} ${cy})`} />
          </g>
        );
      })}
      <text x={X(byKey.get("esi")!.pos[0])} y={Y(byKey.get("esi")!.pos[1]) - 30} textAnchor="middle" className="fill-ink-2 font-mono" fontSize="11">
        {POLICY}
      </text>
    </svg>
  );
}
