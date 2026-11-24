import { cookies } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import FavoriteButton from "@/components/FavoriteButton";
import SiteHeader from "@/components/SiteHeader";
import { getViewer } from "@/lib/viewer";

const backend = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

const TYPE_LABELS: Record<string, string> = {
  verified_biography: "проверенная биография",
  community_story: "история сообщества",
};

const SOURCE_LABELS: Record<string, string> = {
  book: "книга",
  article: "статья",
  interview: "интервью",
  document: "документ",
  video: "видео",
  archive: "архив",
  other: "другое",
};

interface StoryDetail {
  slug: string;
  title: string;
  woman_name: string;
  short_description: string;
  full_text: string;
  story_type: string;
  is_anonymous: boolean;
  country: string | null;
  profession: string | null;
  age: string | null;
  tags: { name: string; group: string }[];
  sources: { title: string; url: string | null; source_type: string }[];
  author: { id: string; display_name: string } | null;
}

async function loadStory(slug: string): Promise<StoryDetail | null> {
  try {
    // cookie нужен чтобы авторка могла открыть свою неопубликованную историю
    const store = await cookies();
    const resp = await fetch(`${backend}/api/v1/stories/${slug}`, {
      headers: { cookie: store.toString() },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return (await resp.json()) as StoryDetail;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const story = await loadStory(slug);
  return {
    title: story ? `${story.title} — не первая` : "история — не первая",
    description: story?.short_description,
  };
}

export default async function StoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const story = await loadStory(slug);
  if (!story) notFound();
  const viewer = await getViewer();

  const byGroup = (group: string) => story.tags.filter((t) => t.group === group);
  const groupTitle: Record<string, string> = {
    themes: "темы",
    obstacles: "сомнения, которые преодолела героиня",
    achievements: "достижения",
    fields: "сферы",
    life_circumstances: "жизненные обстоятельства",
  };

  return (
    <>
      <SiteHeader />
      <main>
        <article>
          <h1>{story.title}</h1>
          <p>
            <FavoriteButton
              slug={story.slug}
              initial={viewer.favoriteSlugs.has(story.slug)}
              canToggle={viewer.isAuthed}
            />
          </p>
          <p>
            {story.is_anonymous ? "имя скрыто" : story.woman_name}
            {story.country ? ` · ${story.country}` : ""}
            {story.profession ? ` · ${story.profession}` : ""}
            {story.age ? ` · ${story.age}` : ""}
            {` · ${TYPE_LABELS[story.story_type] ?? story.story_type}`}
          </p>

          <p>{story.short_description}</p>

          {story.full_text.split(/\n{2,}/).map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}

          {story.tags.length > 0 ? (
            <section>
              <h2>о героине</h2>
              {Object.entries(groupTitle).map(([group, title]) => {
                const names = byGroup(group).map((t) => t.name);
                return names.length > 0 ? (
                  <p key={group}>
                    <b>{title}:</b> {names.join(", ")}
                  </p>
                ) : null;
              })}
            </section>
          ) : null}

          {story.sources.length > 0 ? (
            <section>
              <h2>источники</h2>
              <ul>
                {story.sources.map((s, i) => (
                  <li key={i}>
                    {s.url ? (
                      <a href={s.url} rel="noopener noreferrer">
                        {s.title}
                      </a>
                    ) : (
                      s.title
                    )}{" "}
                    ({SOURCE_LABELS[s.source_type] ?? s.source_type})
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </article>

        {story.author ? (
          <p>
            авторка истории:{" "}
            <Link href={`/u/${story.author.id}`}>{story.author.display_name}</Link>
          </p>
        ) : null}

        <p>
          <Link href="/catalog">← в каталог</Link>
        </p>
      </main>
    </>
  );
}
