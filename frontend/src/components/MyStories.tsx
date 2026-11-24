"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

interface MyStoryCard {
  slug: string;
  title: string;
  short_description: string;
  story_type: string;
  verification_status: string;
  publication_status: string;
  created_at: string;
  country: string | null;
  profession: string | null;
}

// статусная подпись для авторки: без внутреннего жаргона
const STATUS_LABEL: Record<string, string> = {
  "pending|draft": "на модерации",
  "pending|published": "на модерации",
  "verified|published": "опубликована",
  "verified|draft": "готова к публикации",
  "rejected|draft": "отклонена",
  "rejected|published": "отклонена",
  "needs_revision|published": "на доработке",
  "needs_revision|draft": "на доработке",
  "archived|published": "в архиве",
  "archived|draft": "в архиве",
};

const FILTERS = [
  { key: "all", label: "все" },
  { key: "published", label: "опубликованные" },
  { key: "pending", label: "на модерации" },
  { key: "official", label: "официальные" },
  { key: "draft", label: "черновики и прочее" },
];

export default function MyStories() {
  const [items, setItems] = useState<MyStoryCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetch("/api/v1/profile/stories")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("не удалось загрузить"))))
      .then((d) => setItems(d.items ?? []))
      .catch((e: Error) => setError(e.message));
  }, []);

  const visible = useMemo(() => {
    if (!items) return [];
    if (filter === "all") return items;
    if (filter === "published")
      return items.filter(
        (s) => s.publication_status === "published" && s.verification_status === "verified"
      );
    if (filter === "pending") return items.filter((s) => s.verification_status === "pending");
    if (filter === "official") return items.filter((s) => s.story_type === "verified_biography");
    return items.filter((s) => s.verification_status !== "verified");
  }, [items, filter]);

  const statusOf = (s: MyStoryCard) =>
    STATUS_LABEL[`${s.verification_status}|${s.publication_status}`] ?? s.verification_status;

  return (
    <details>
      <summary>мои истории{items ? ` (${items.length})` : ""}</summary>

      <p>
        <button type="button" onClick={() => setShowFilters(!showFilters)}>
          {showFilters ? "скрыть фильтры" : "показать фильтры"}
        </button>
      </p>

      {showFilters ? (
        <p>
          {FILTERS.map((f) => (
            <label key={f.key} style={{ marginRight: "0.6rem" }}>
              <input
                type="radio"
                name="my-stories-filter"
                checked={filter === f.key}
                onChange={() => setFilter(f.key)}
              />{" "}
              {f.label}
            </label>
          ))}
        </p>
      ) : null}

      {error ? <p>{error}</p> : null}
      {items === null && !error ? <p>загружаем…</p> : null}

      {visible.length === 0 && items !== null ? (
        <p>
          пока ничего нет. поделиться своей историей можно на{" "}
          <Link href="/">главной</Link>
        </p>
      ) : null}

      {visible.map((s) => (
        <article key={s.slug} style={{ borderTop: "1px solid #ddd", paddingTop: "0.5rem" }}>
          <h3>
            <Link href={`/stories/${s.slug}`}>{s.title}</Link>
          </h3>
          <p>
            {s.country ?? ""}
            {s.profession ? ` · ${s.profession}` : ""} · {statusOf(s)}
          </p>
          <p>{s.short_description}</p>
        </article>
      ))}
    </details>
  );
}
