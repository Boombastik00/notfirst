import { cookies } from "next/headers";

// общая серверная проверка «кто сейчас смотрит» для страниц каталога и историй
const backend = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export interface Viewer {
  isAuthed: boolean;
  favoriteSlugs: Set<string>;
}

export async function getViewer(): Promise<Viewer> {
  const store = await cookies();
  const cookieHeader = store.toString();
  if (!cookieHeader.includes("nf_session")) {
    return { isAuthed: false, favoriteSlugs: new Set() };
  }

  try {
    const [meResp, favResp] = await Promise.all([
      fetch(`${backend}/api/v1/auth/me`, {
        headers: { cookie: cookieHeader },
        cache: "no-store",
      }),
      fetch(`${backend}/api/v1/favorites`, {
        headers: { cookie: cookieHeader },
        cache: "no-store",
      }),
    ]);
    if (!meResp.ok) {
      return { isAuthed: false, favoriteSlugs: new Set() };
    }
    const slugs = favResp.ok
      ? (((await favResp.json()).items as { slug: string }[]).map((i) => i.slug))
      : [];
    return { isAuthed: true, favoriteSlugs: new Set(slugs) };
  } catch {
    return { isAuthed: false, favoriteSlugs: new Set() };
  }
}
