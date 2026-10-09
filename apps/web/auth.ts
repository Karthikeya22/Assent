import NextAuth, { type DefaultSession } from "next-auth";
import "next-auth/jwt"; // brings the module into scope for the JWT augmentation below
import Credentials from "next-auth/providers/credentials";

export type Role = "coordinator" | "clinician" | "policy_admin" | "auditor";

declare module "next-auth" {
  interface User {
    role: Role;
    orgId: string;
    accessToken: string;
    accessTokenExpires: number;
  }
  interface Session {
    accessToken: string;
    user: { id: string; role: Role; orgId: string } & DefaultSession["user"];
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    uid: string;
    role: Role;
    orgId: string;
    accessToken: string;
    accessTokenExpires: number;
  }
}

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export const { handlers, auth, signIn, signOut } = NextAuth({
  pages: { signIn: "/login" },
  session: { strategy: "jwt" },
  providers: [
    Credentials({
      credentials: { email: {}, password: {} },
      async authorize(c) {
        const res = await fetch(`${API_URL}/api/v1/auth/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: c.email, password: c.password }),
        });
        if (!res.ok) return null;
        const t = await res.json();
        return {
          id: t.user.id,
          email: t.user.email,
          name: t.user.name,
          role: t.user.role,
          orgId: t.user.org_id,
          accessToken: t.access_token,
          accessTokenExpires: Date.now() + t.expires_in * 1000,
        };
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        return {
          ...token,
          uid: user.id!,
          role: user.role,
          orgId: user.orgId,
          accessToken: user.accessToken,
          accessTokenExpires: user.accessTokenExpires,
        };
      }
      // shortcut: no refresh token yet, so the session ends when the 15-min API token does;
      // add a /auth/refresh endpoint before the demo goes public.
      if (Date.now() > token.accessTokenExpires) return null;
      return token;
    },
    session({ session, token }) {
      session.accessToken = token.accessToken;
      session.user.id = token.uid;
      session.user.role = token.role;
      session.user.orgId = token.orgId;
      return session;
    },
    authorized({ auth, request }) {
      return request.nextUrl.pathname.startsWith("/app") ? !!auth : true;
    },
  },
});
