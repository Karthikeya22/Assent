"use server";

const CDS_URL = process.env.CDS_URL ?? "http://localhost:8010";

export type Card = {
  summary: string;
  indicator: "info" | "warning" | "critical";
  detail: string;
  links: { label: string; url: string }[];
};

/** What an EHR does on order sign: call the registered CDS service with the draft order. */
export async function signOrder(
  patientId: string,
  cpt: string,
  icd10: string,
): Promise<{ cards: Card[]; error?: string }> {
  const body = {
    hook: "order-sign",
    hookInstance: crypto.randomUUID(),
    context: {
      userId: "Practitioner/demo",
      patientId,
      draftOrders: {
        resourceType: "Bundle",
        entry: [
          {
            resource: {
              resourceType: "ServiceRequest",
              status: "draft",
              intent: "order",
              code: { coding: [{ system: "http://www.ama-assn.org/go/cpt", code: cpt }] },
              reasonCode: [{ coding: [{ system: "http://hl7.org/fhir/sid/icd-10-cm", code: icd10 }] }],
              subject: { reference: `Patient/${patientId}` },
            },
          },
        ],
      },
    },
  };
  try {
    const r = await fetch(`${CDS_URL}/cds-services/assent-order-sign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!r.ok) return { cards: [], error: `CDS service returned ${r.status}` };
    return { cards: (await r.json()).cards as Card[] };
  } catch {
    return { cards: [], error: "CDS service unreachable (start it on :8010)" };
  }
}
