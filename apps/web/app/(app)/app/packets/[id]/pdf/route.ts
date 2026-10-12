import { api } from "@/lib/api/client";

/** Streams the packet PDF with the user's session token (the API needs a bearer header). */
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { data, response } = await (await api()).GET("/api/v1/packets/{packet_id}", {
    params: { path: { packet_id: id }, query: { format: "pdf" } },
    parseAs: "arrayBuffer",
  });
  if (!data) return new Response("Not found", { status: response.status });
  return new Response(data as ArrayBuffer, {
    headers: { "Content-Type": "application/pdf", "Content-Disposition": `inline; filename="packet-${id}.pdf"` },
  });
}
