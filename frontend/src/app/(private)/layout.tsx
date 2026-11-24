import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

// приватные страницы проверяют сессию на сервере ещё до рендера
const backend = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export default async function PrivateLayout({ children }: { children: ReactNode }) {
  const store = await cookies();
  let ok = false;
  try {
    const resp = await fetch(`${backend}/api/v1/auth/me`, {
      headers: { cookie: store.toString() },
      cache: "no-store",
    });
    ok = resp.ok;
  } catch {
    ok = false;
  }
  if (!ok) redirect("/login");

  return <>{children}</>;
}
