import Link from "next/link";

import GlobalSearch from "@/components/GlobalSearch";
import HomeActions from "@/components/HomeActions";
import SiteHeader from "@/components/SiteHeader";
import { getViewer } from "@/lib/viewer";

const backend = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

interface TagInfo {
  id: number;
  group_code: string;
  parent_id: number | null;
  name_ru: string;
}

interface DailyStory {
  story: {
    slug: string;
    title: string;
    woman_name: string;
    short_description: string;
    is_anonymous: boolean;
    country: string | null;
    profession: string | null;
  };
}

export default async function HomePage() {
  const viewer = await getViewer();

  const [tagsResp, dailyResp] = await Promise.all([
    fetch(`${backend}/api/v1/tags`, { cache: "no-store" }),
    fetch(`${backend}/api/v1/stories/daily`, { cache: "no-store" }),
  ]);
  const tags = tagsResp.ok ? ((await tagsResp.json()) as TagInfo[]) : [];
  const daily = dailyResp.ok ? ((await dailyResp.json()) as DailyStory) : null;

  const byGroup = (code: string) =>
    tags.filter((t) => t.group_code === code).map((t) => ({ id: t.id, name_ru: t.name_ru }));

  const obstacleCategories = tags
    .filter((t) => t.group_code === "obstacles" && t.parent_id === null)
    .map((cat) => ({
      id: cat.id,
      name_ru: cat.name_ru,
      children: tags
        .filter((t) => t.group_code === "obstacles" && t.parent_id === cat.id)
        .map((t) => ({ id: t.id, name_ru: t.name_ru })),
    }));

  return (
    <>
      <SiteHeader />
      <main>
        <h1>не первая</h1>
        <p>истории женщин, с которыми можно себя соотнести</p>

        <GlobalSearch />

        {daily ? (
          <section>
            <h2>история дня</h2>
            <article>
              <h3>
                <Link href={`/stories/${daily.story.slug}`}>{daily.story.title}</Link>
              </h3>
              <p>
                {daily.story.is_anonymous ? "имя скрыто" : daily.story.woman_name}
                {daily.story.country ? ` · ${daily.story.country}` : ""}
                {daily.story.profession ? ` · ${daily.story.profession}` : ""}
              </p>
              <p>{daily.story.short_description}</p>
            </article>
          </section>
        ) : null}

        {viewer.isAuthed ? (
          <HomeActions
            options={{
              professions: byGroup("professions"),
              fields: byGroup("fields"),
              obstacleCategories,
            }}
            favoriteSlugs={[...viewer.favoriteSlugs]}
          />
        ) : (
          <nav>
            <p>
              <Link href="/catalog">перейти в каталог историй</Link>
            </p>
            <p>
              <Link href="/login">войти, чтобы получать персональные подборки</Link>
            </p>
          </nav>
        )}
      </main>
    </>
  );
}
