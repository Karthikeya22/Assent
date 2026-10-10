import { auth } from "@/auth";

export const dynamic = "force-dynamic";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

// Same-origin SSE proxy: the browser's EventSource can't send an Authorization header, and a
// token in the URL would end up in logs. The JWT stays server-side here.
export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth();
  if (!session) return new Response("Unauthorized", { status: 401 });
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) return new Response("Bad run id", { status: 400 });

  const upstream = await fetch(`${API_URL}/api/v1/runs/${id}/stream`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    signal: req.signal,
    cache: "no-store",
  });
  if (!upstream.ok || !upstream.body) {
    return new Response(await upstream.text(), { status: upstream.status });
  }
  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}
