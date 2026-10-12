import type { Metadata } from "next";
import { api } from "@/lib/api/client";
import { EhrSim } from "./EhrSim";

export const metadata: Metadata = { title: "EHR simulator" };

export default async function EhrSimPage() {
  const { data } = await (await api()).GET("/api/v1/cases", { params: { query: { limit: 100 } } });
  const seen = new Set<string>();
  const patients = (data?.items ?? [])
    .filter((c) => c.patient_fhir_id && !seen.has(c.patient_fhir_id) && seen.add(c.patient_fhir_id))
    .map((c) => ({ id: c.patient_fhir_id, name: c.patient_name, cpt: c.cpt_codes[0], icd10: c.icd10_codes[0] }));
  return <EhrSim patients={patients} />;
}
