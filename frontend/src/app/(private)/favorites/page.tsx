import { cookies } from "next/headers";
import Link from "next/link";
import { Suspense } from "react";

import FavoriteButton from "@/components/FavoriteButton";
import FilterPanel, { type FilterGroups } from "@/components/FilterPanel";
import SiteHeader from "@/components/SiteHeader";

const backend = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

const TYPE_LABELS: Record<string, string> = {
  verified_biography: "проверенная биография",
  community_story: "история сообщества",
};

const FILTER_KEYS = [
  "q",
  "country",
  "profession",
  "field",
  "obstacle",
  "theme",
  "story_type",
  "sort",
] as const;

interface FavoriteCard {
  slug: string;
  title: string;
  woman_name: string;
  short_description: string;
  story_type: string;
  is_anonymous: boolean;
  country: string | null;
  profession: string | null;
}

interface TagInfo {
  id: number;
  group_code: string;
  parent_id: number | null;
  name_ru: string;
}

const num = (raw: string | undefined) => {
  const parsed = raw ? Number(raw) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
};

async function loadFavorites(searchParams: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = searchParams[key];
    if (value) qs.set(key, value);
  }

  try {
    const [favResp, tagsResp] = await Promise.all([
      fetch(`${backend}/api/v1/favorites?${qs.toString()}`, {
        headers: { cookie: (await cookies()).toString() },
        cache: "no-store",
      }),
      fetch(`${backend}/api/v1/tags`, { cache: "no-store" }),
    ]);
    if (!favResp.ok || !tagsResp.ok) {
      return { error: "не удалось загрузить" } as const;
    }

    const items = ((await favResp.json()).items as FavoriteCard[]) ?? [];
    const tags = (await tagsResp.json()) as TagInfo[];

    const byGroup = (code: string) =>
      tags.filter((t) => t.group_code === code).map((t) => ({ id: t.id, name_ru: t.name_ru }));

    const byId = new Map(tags.map((t) => [t.id, t]));
    const options: FilterGroups = {
      countries: byGroup("countries"),
      professions: byGroup("professions"),
      fields: byGroup("fields"),
      obstacles: tags
        .filter((t) => t.group_code === "obstacles")
        .map((t) => ({
          id: t.id,
          name_ru: t.parent_id
            ? `${t.name_ru} — ${byId.get(t.parent_id)?.name_ru ?? ""}`
            : t.name_ru,
        })),
      themes: byGroup("themes"),
    };
    return { items, options } as const;
  } catch {
    return { error: "не удалось загрузить" } as const;
  }
}

export default async function FavoritesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const loaded = await loadFavorites(sp);

  return (
    <>
      <SiteHeader />
      <main>
        <h1>сохранённые истории</h1>

        {"error" in loaded ? (
          <p>{loaded.error}</p>
        ) : (
          <>
            {/* фильтры спрятаны чтобы не мешались, список и так всегда под рукой */}
            <details>
              <summary>фильтры</summary>
              <Suspense fallback={<p>фильтры загружаются…</p>}>
                <FilterPanel
                  options={loaded.options}
                  basePath="/favorites"
                  useShow={false}
                  sortVariants={[
                    { value: "saved", label: "по времени сохранения" },
                    { value: "new", label: "сначала новые" },
                    { value: "old", label: "сначала старые" },
                    { value: "title", label: "по заголовку" },
                  ]}
                  initial={{
                    q: sp.q ?? "",
                    country: num(sp.country),
                    profession: num(sp.profession),
                    field: num(sp.field),
                    obstacle: num(sp.obstacle),
                    theme: num(sp.theme),
                    story_type: sp.story_type ?? "",
                    sort: sp.sort ?? "saved",
                  }}
                />
              </Suspense>
            </details>

            {loaded.items.length === 0 ? (
              <p>
                {Object.keys(sp).length > 0
                  ? "по таким фильтрам ничего не нашлось"
                  : "пока ничего не сохранено. выбери истории в каталоге и нажми «сохранить»"}
              </p>
            ) : (
              loaded.items.map((s) => (
                <article key={s.slug}>
                  <h2>
                    <Link href={`/stories/${s.slug}`}>{s.title}</Link>
                  </h2>
                  <p>
                    {s.is_anonymous ? "имя скрыто" : s.woman_name}
                    {s.country ? ` · ${s.country}` : ""}
                    {s.profession ? ` · ${s.profession}` : ""}
                    {` · ${TYPE_LABELS[s.story_type] ?? s.story_type}`}
                  </p>
                  <p>{s.short_description}</p>
                  <FavoriteButton slug={s.slug} initial={true} canToggle={true} />
                </article>
              ))
            )}
          </>
        )}

        <p>
          <Link href="/">← на главную</Link>
        </p>
      </main>
    </>
  );
}
