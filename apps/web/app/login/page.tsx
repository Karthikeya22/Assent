import { AuthError } from "next-auth";
import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { signIn } from "@/auth";

export const metadata: Metadata = { title: "Sign in" };

async function login(formData: FormData) {
  "use server";
  try {
    await signIn("credentials", {
      email: formData.get("email"),
      password: formData.get("password"),
      redirectTo: "/app/worklist",
    });
  } catch (e) {
    if (e instanceof AuthError) redirect("/login?error=1");
    throw e; // signIn's success path throws a redirect; let it through
  }
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const field =
    "mt-1.5 h-10 w-full rounded-[var(--radius-control)] border border-rule bg-paper-raised px-3 text-md text-ink placeholder:text-ink-3";

  return (
    <main className="grid min-h-dvh place-items-center px-6">
      <div className="w-full max-w-sm">
        <Link href="/" className="display text-2xl">
          Assent
        </Link>
        <p className="mt-2 text-ink-2">Sign in to the coordinator workspace.</p>

        <form action={login} className="mt-8 space-y-4">
          <label className="block">
            <span className="text-sm text-ink-2">Email</span>
            <input
              name="email"
              type="email"
              required
              autoComplete="username"
              defaultValue="coordinator@assent.dev"
              className={field}
            />
          </label>
          <label className="block">
            <span className="text-sm text-ink-2">Password</span>
            <input
              name="password"
              type="password"
              required
              autoComplete="current-password"
              className={field}
            />
          </label>
          {error && (
            <p role="alert" className="text-sm text-fail">
              That email and password don’t match.
            </p>
          )}
          <button
            type="submit"
            className="h-10 w-full rounded-[var(--radius-control)] bg-signal font-medium text-paper transition-opacity duration-[var(--dur-1)] hover:opacity-90"
          >
            Sign in
          </button>
        </form>

        <p className="mt-8 font-mono text-xs text-ink-3">
          Synthetic patients only. No PHI. Demo password: assent-dev
        </p>
      </div>
    </main>
  );
}
