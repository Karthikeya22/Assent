import createClient from "openapi-fetch";
import { auth } from "@/auth";
import type { paths } from "./schema";

const baseUrl = process.env.API_URL ?? "http://localhost:8000";

/** Server-side typed client for the FastAPI backend, authenticated as the current session user. */
export async function api() {
  const session = await auth();
  return createClient<paths>({
    baseUrl,
    headers: session ? { Authorization: `Bearer ${session.accessToken}` } : {},
  });
}
