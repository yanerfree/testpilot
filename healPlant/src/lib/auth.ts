import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        username: { label: "用户名", type: "text" },
        password: { label: "密码", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) return null;

        const { compare } = await import("bcryptjs");
        const { db } = await import("./db");
        const { admin } = await import("./db/schema");
        const { eq } = await import("drizzle-orm");

        const [user] = await db
          .select()
          .from(admin)
          .where(eq(admin.username, credentials.username as string))
          .limit(1);

        if (!user) return null;

        const isValid = await compare(
          credentials.password as string,
          user.passwordHash
        );
        if (!isValid) return null;

        return { id: String(user.id), name: user.username };
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60,
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isAdmin = nextUrl.pathname.startsWith("/admin");
      const isAdminApi = nextUrl.pathname.startsWith("/api/admin");

      if (isAdmin || isAdminApi) {
        return isLoggedIn;
      }
      return true;
    },
  },
});
