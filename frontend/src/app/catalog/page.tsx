import Link from "next/link";
import { Suspense } from "react";

import FavoriteButton from "@/components/FavoriteButton";
import FilterPanel, { type FilterGroups } from "@/components/FilterPanel";
import SiteHeader from "@/components/SiteHeader";
import { getViewer } from "@/lib/viewer";

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
  "page",
  "limit",
] as const;

interface StoryCard {
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

async function loadCatalog(searchParams: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = searchParams[key];
    if (value) qs.set(key, value);
  }

  const [storiesResp, tagsResp] = await Promise.all([
    fetch(`${backend}/api/v1/stories?${qs.toString()}`, { cache: "no-store" }),
    fetch(`${backend}/api/v1/tags`, { cache: "no-store" }),
  ]);

  if (!storiesResp.ok || !tagsResp.ok) {
    return { error: "не удалось загрузить каталог" } as const;
  }

  const data = (await storiesResp.json()) as {
    items: StoryCard[];
    total: number;
    page: number;
    pages: number;
  };
  const tags = (await tagsResp.json()) as TagInfo[];

  const byGroup = (code: string) =>
    tags.filter((t) => t.group_code === code).map((t) => ({ id: t.id, name_ru: t.name_ru }));

  const byId = new Map(tags.map((t) => [t.id, t]));
  const obstacles = tags
    .filter((t) => t.group_code === "obstacles")
    .map((t) => ({
      id: t.id,
      name_ru: t.parent_id
        ? `${t.name_ru} — ${byId.get(t.parent_id)?.name_ru ?? ""}`
        : t.name_ru,
    }));

  const options: FilterGroups = {
    countries: byGroup("countries"),
    professions: byGroup("professions"),
    fields: byGroup("fields"),
    obstacles,
    themes: byGroup("themes"),
  };

  return { data, options, qs } as const;
}

const num = (raw: string | undefined) => {
  const parsed = raw ? Number(raw) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
};

export default async function CatalogPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const loaded = await loadCatalog(sp);
  const viewer = await getViewer();
  // список показываем только после явного «найти» — страница не захламляется сразу
  const showResults = sp.show === "1";

  return (
    <>
      <SiteHeader />
      <main>
        <h1>каталог историй</h1>

        {"error" in loaded ? (
          <p>{loaded.error}</p>
        ) : (
          <>
            <Suspense fallback={<p>фильтры загружаются…</p>}>
              <FilterPanel
                options={loaded.options}
                initial={{
                  q: sp.q ?? "",
                  country: num(sp.country),
                  profession: num(sp.profession),
                  field: num(sp.field),
                  obstacle: num(sp.obstacle),
                  theme: num(sp.theme),
                  story_type: sp.story_type ?? "",
                  sort: sp.sort ?? "new",
                }}
              />
            </Suspense>

            {showResults ? (
              <>
                <p>
                  {loaded.data.total === 0
                    ? "по таким фильтрам ничего не нашлось"
                    : `историй: ${loaded.data.total}`}
                </p>

                {loaded.data.items.map((s) => (
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
                    <FavoriteButton
                      slug={s.slug}
                      initial={viewer.favoriteSlugs.has(s.slug)}
                      canToggle={viewer.isAuthed}
                    />
                  </article>
                ))}

                <nav>
                  {loaded.data.page > 1 ? (
                    <Link
                      href={`/catalog?${withPage(loaded.qs, loaded.data.page - 1)}`}
                      aria-label="предыдущая страница"
                    >
                      ← назад
                    </Link>
                  ) : null}{" "}
                  страница {loaded.data.page} из {loaded.data.pages}{" "}
                  {loaded.data.page < loaded.data.pages ? (
                    <Link
                      href={`/catalog?${withPage(loaded.qs, loaded.data.page + 1)}`}
                      aria-label="следующая страница"
                    >
                      вперёд →
                    </Link>
                  ) : null}
                </nav>
              </>
            ) : (
              <p>выбери фильтры и нажми «найти истории» — или ищи сразу по всем</p>
            )}
          </>
        )}

        <p>
          <Link href="/">← вернуться на главную</Link>
        </p>
      </main>
    </>
  );
}

function withPage(qs: URLSearchParams, page: number): string {
  const copy = new URLSearchParams(qs.toString());
  if (page > 1) copy.set("page", String(page));
  else copy.delete("page");
  copy.set("show", "1");
  return copy.toString();
}
