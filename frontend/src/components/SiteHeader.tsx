import { cookies } from "next/headers";
import Link from "next/link";

import LogoutButton from "./LogoutButton";
import type { MeInfo } from "@/lib/api";

const MODERATION_ROLES = new Set(["admin", "moderator"]);
// окно «истории» — написание официальных историй, авторкам и создательнице
const AUTHOR_ROLES = new Set(["admin", "editor"]);
// ссылка на sqladmin видна всему стаффу, вход туда всё равно ограничен ролями
const STAFF_ROLES = new Set(["admin", "editor", "moderator"]);

// в dev админка живёт на порту api, в prod будет /admin/ за общей точкой входа
const ADMIN_URL = process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:8000/admin/";

async function fetchMe(): Promise<MeInfo | null> {
  const backend = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";
  try {
    const store = await cookies();
    const resp = await fetch(`${backend}/api/v1/auth/me`, {
      headers: { cookie: store.toString() },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return (await resp.json()) as MeInfo;
  } catch {
    return null;
  }
}

export default async function SiteHeader() {
  const me = await fetchMe();

  return (
    <header>
      <nav>
        <ul>
          <li>
            <Link href="/">не первая</Link>
          </li>
          <li>
            <Link href="/catalog">каталог</Link>
          </li>
          {me ? (
            <>
              <li>
                <Link href="/profile">
                  профиль
                  {me.display_name ? `: ${me.display_name}` : ""}
                  {me.has_rejection_notice ? "!" : ""}
                </Link>
              </li>
              <li>
                <Link href="/favorites">сохранённое</Link>
              </li>
              {MODERATION_ROLES.has(me.role) ? (
                <li>
                  <Link href="/moderation">модерация</Link>
                </li>
              ) : null}
              {AUTHOR_ROLES.has(me.role) ? (
                <li>
                  <Link href="/write">истории</Link>
                </li>
              ) : null}
              {STAFF_ROLES.has(me.role) ? (
                <li>
                  <a href={ADMIN_URL}>админка</a>
                </li>
              ) : null}
              <li>
                <LogoutButton />
              </li>
            </>
          ) : (
            <li>
              <Link href="/login">войти</Link>
            </li>
          )}
        </ul>
      </nav>
    </header>
  );
}
