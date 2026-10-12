const TIMELINE = [
  { when: "Jan 2026", what: "CMS-0057-F decision timeframes for impacted payers", src: 4 },
  { when: "Jan 2026", what: "WISeR model begins in six states", src: 2 },
  { when: "Jan 2027", what: "FHIR Prior Authorization API required", src: 4 },
];
const TAGS = [
  { tag: "HL7 FHIR R4", line: "Charts are read as FHIR resources; packets are FHIR Bundles." },
  { tag: "CDS Hooks", line: "An order-sign hook shows prior-auth requirements inside the EHR." },
  { tag: "Da Vinci PAS", line: "Packets are Claim(use=preauthorization) bundles with evidence attached." },
  { tag: "SMART on FHIR", line: "The launch model for running inside an EHR session (planned)." },
];

export function Standards() {
  return (
    <section id="standards" aria-labelledby="standards-title" className="mx-auto max-w-6xl px-6 py-24 md:py-40">
      <h2 id="standards-title" className="display text-4xl md:text-5xl">Built on the standards payers must adopt.</h2>
      <ol className="mt-12 grid gap-8 border-t border-rule pt-8 md:grid-cols-3">
        {TIMELINE.map((t) => (
          <li key={t.what}>
            <p className="font-mono text-sm text-signal">{t.when}</p>
            <p className="mt-2 text-ink">
              {t.what}
              <a href={`#source-${t.src}`} className="ml-0.5 align-super font-mono text-xs text-ink-3 hover:text-ink">{t.src}</a>
            </p>
          </li>
        ))}
      </ol>
      <dl className="mt-14 grid gap-6 sm:grid-cols-2">
        {TAGS.map((t) => (
          <div key={t.tag}>
            <dt className="font-mono text-sm text-ink">{t.tag}</dt>
            <dd className="mt-1 text-sm text-ink-2">{t.line}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
