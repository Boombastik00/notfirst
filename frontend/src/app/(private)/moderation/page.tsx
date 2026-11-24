"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { apiFetch } from "@/lib/api";

interface PendingStory {
  id: string;
  slug: string;
  title: string;
  text: string;
  created_by: string | null;
  created_at: string;
}

export default function ModerationPage() {
  const [items, setItems] = useState<PendingStory[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function reload() {
    try {
      const data = await apiFetch<PendingStory[]>("/api/v1/moderation/pending");
      setItems(data);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function act(id: string, action: "publish" | "reject") {
    setError(null);
    setNotice(null);
    try {
      await apiFetch(`/api/v1/moderation/${id}/${action}`, { method: "POST" });
      setNotice(action === "publish" ? "история опубликована" : "история отклонена и удалена");
      await reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main>
      <h1>модерация историй</h1>
      <p>здесь появляются пользовательские истории до публикации</p>
      {notice ? <p role="status">{notice}</p> : null}
      {error ? <p>{error}</p> : null}

      {items === null ? (
        <p>загружаем…</p>
      ) : items.length === 0 ? (
        <p>новых историй нет</p>
      ) : (
        items.map((s) => (
          <article key={s.id}>
            <h2>{s.title}</h2>
            <p>{new Date(s.created_at).toLocaleString("ru-RU")}</p>
            {s.text.split(/\n{2,}/).map((p, i) => (
              <p key={i}>{p}</p>
            ))}
            <p>
              <button type="button" onClick={() => act(s.id, "publish")}>
                опубликовать
              </button>{" "}
              <button type="button" onClick={() => act(s.id, "reject")}>
                отклонить
              </button>
            </p>
          </article>
        ))
      )}

      <p>
        <Link href="/">← на главную</Link>
      </p>
    </main>
  );
}
