import { cookies } from "next/headers";
import Link from "next/link";
import type { Metadata } from "next";

import SiteHeader from "@/components/SiteHeader";
import StaffPanel from "@/components/StaffPanel";

const backend = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

interface Badge {
  code: string;
  label: string;
}

interface PublicProfile {
  id: string;
  display_name: string;
  avatar_url: string | null;
  badges: Badge[];
  is_banned: boolean;
  current_field: string | null;
  bio: string | null;
}

interface PublicStoryCard {
  slug: string;
  title: string;
  short_description: string;
  story_type: string;
  country: string | null;
  profession: string | null;
}

const TYPE_LABELS: Record<string, string> = {
  verified_biography: "проверенная биография",
  community_story: "история сообщества",
};

async function fetchJson<T>(path: string, cookieHeader: string): Promise<T | null> {
  try {
    const resp = await fetch(`${backend}${path}`, {
      headers: { cookie: cookieHeader },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return (await resp.json()) as T;
  } catch {
    return null;
  }
}

async function loadProfile(id: string) {
  const store = await cookies();
  const cookieHeader = store.toString();

  const [profile, stories, catalog, me] = await Promise.all([
    fetchJson<PublicProfile>(`/api/v1/u/${id}`, ""),
    fetchJson<{ items: PublicStoryCard[] }>(`/api/v1/u/${id}/stories`, ""),
    fetchJson<{ items: Badge[] }>("/api/v1/u/badges", cookieHeader),
    fetchJson<{ role: string; id: string }>("/api/v1/auth/me", cookieHeader),
  ]);
  return { profile, stories, catalog, me };
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const { profile } = await loadProfile(id);
  return {
    title: profile ? `${profile.display_name} — не первая` : "профиль — не первая",
  };
}

export default async function PublicProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { profile, stories, catalog, me } = await loadProfile(id);

  if (!profile) {
    return (
      <>
        <SiteHeader />
        <main>
          <h1>профиль</h1>
          <p>профиль не найден</p>
          <p>
            <Link href="/catalog">← в каталог</Link>
          </p>
        </main>
      </>
    );
  }

  // панель выдачи префиксов и банов — модераторшам и создательнице
  const isStaff = me?.role === "admin" || me?.role === "moderator";

  const name = profile.display_name;
  const storiesTitle = `истории (${name})`;

  return (
    <>
      <SiteHeader />
      <main>
        <h1>{name}</h1>

        {profile.badges.length > 0 ? (
          <p>
            {profile.badges.map((b) => (
              <span
                key={b.code}
                style={{
                  display: "inline-block",
                  border: "1px solid #888",
                  borderRadius: "1em",
                  padding: "0 0.6em",
                  marginRight: "0.4rem",
                }}
              >
                {b.label}
              </span>
            ))}
          </p>
        ) : null}

        {profile.is_banned ? <p>аккаунт заблокирован</p> : null}

        {profile.current_field || profile.bio ? (
          <section>
            <h2>дополнительная информация</h2>
            {profile.current_field ? <p>сфера деятельности: {profile.current_field}</p> : null}
            {profile.bio ? <p>о себе: {profile.bio}</p> : null}
          </section>
        ) : null}

        {isStaff && catalog ? (
          <StaffPanel
            userId={profile.id}
            displayName={name}
            catalog={catalog.items}
            currentBadges={profile.badges.map((b) => b.code)}
            isBanned={profile.is_banned}
          />
        ) : null}

        <section>
          <h2>{storiesTitle}</h2>
          {stories === null || stories.items.length === 0 ? (
            <p>опубликованных историй пока нет</p>
          ) : (
            stories.items.map((s) => (
              <article key={s.slug} style={{ borderTop: "1px solid #ddd", paddingTop: "0.5rem" }}>
                <h3>
                  <Link href={`/stories/${s.slug}`}>{s.title}</Link>
                </h3>
                <p>
                  {s.country ?? ""}
                  {s.profession ? ` · ${s.profession}` : ""}
                  {` · ${TYPE_LABELS[s.story_type] ?? s.story_type}`}
                </p>
                <p>{s.short_description}</p>
              </article>
            ))
          )}
        </section>

        <p>
          <Link href="/catalog">← в каталог</Link>
        </p>
      </main>
    </>
  );
}
