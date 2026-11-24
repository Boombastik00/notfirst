"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import Modal from "@/components/Modal";
import { apiFetch } from "@/lib/api";

interface StoryCard {
  slug: string;
  title: string;
  woman_name: string;
  short_description: string;
  is_anonymous: boolean;
  country: string | null;
  profession: string | null;
}

interface AccountCard {
  id: string;
  display_name: string;
  badges: { code: string; label: string }[];
}

// поиск на главной: строка с вводом, по энтеру или кнопке открывается окно
// с вкладками «истории» и «аккаунты»
export default function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"stories" | "accounts">("stories");
  const [stories, setStories] = useState<StoryCard[] | null>(null);
  const [accounts, setAccounts] = useState<AccountCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const q = query.trim();

  async function loadStories() {
    setStories(null);
    setError(null);
    try {
      const data = await apiFetch<{ items: StoryCard[] }>(
        `/api/v1/stories?q=${encodeURIComponent(q)}&limit=20`,
      );
      setStories(data.items);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function loadAccounts() {
    setAccounts(null);
    setError(null);
    try {
      const data = await apiFetch<AccountCard[]>(
        `/api/v1/u/search?q=${encodeURIComponent(q)}`,
      );
      setAccounts(data);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // при открытии грузим активную вкладку, при переключении — её же
  useEffect(() => {
    if (!open || q.length < 2) return;
    if (tab === "stories" && stories === null) loadStories();
    if (tab === "accounts" && accounts === null) loadAccounts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, tab]);

  function startSearch() {
    if (q.length < 2) return;
    setStories(null);
    setAccounts(null);
    setTab("stories");
    setOpen(true);
  }

  function switchTab(next: "stories" | "accounts") {
    setTab(next);
    if (next === "stories" && stories === null) loadStories();
    if (next === "accounts" && accounts === null) loadAccounts();
  }

  function close() {
    setOpen(false);
  }

  return (
    <section>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          startSearch();
        }}
      >
        <label htmlFor="global-search" style={{ display: "block" }}>
          поиск по историям и аккаунтам:{" "}
        </label>
        <input
          id="global-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={100}
          placeholder="введи слово или ник"
        />{" "}
        <button type="submit" disabled={q.length < 2}>
          искать
        </button>
      </form>
      {q.length > 0 && q.length < 2 ? (
        <p>введи хотя бы пару букв</p>
      ) : null}

      {open ? (
        <Modal title={`поиск: ${q}`} onClose={close}>
          <p>
            <button
              type="button"
              onClick={() => switchTab("stories")}
              aria-pressed={tab === "stories"}
              style={{ fontWeight: tab === "stories" ? "bold" : "normal" }}
            >
              истории
            </button>{" "}
            <button
              type="button"
              onClick={() => switchTab("accounts")}
              aria-pressed={tab === "accounts"}
              style={{ fontWeight: tab === "accounts" ? "bold" : "normal" }}
            >
              аккаунты
            </button>
          </p>

          {error ? <p>{error}</p> : null}

          {tab === "stories" ? (
            stories === null ? (
              <p>ищем…</p>
            ) : stories.length === 0 ? (
              <p>ничего не найдено</p>
            ) : (
              stories.map((s) => (
                <article
                  key={s.slug}
                  style={{ borderTop: "1px solid #ddd", paddingTop: "0.5rem" }}
                >
                  <h3>
                    <Link href={`/stories/${s.slug}`} onClick={close}>
                      {s.title}
                    </Link>
                  </h3>
                  <p>
                    {s.is_anonymous ? "имя скрыто" : s.woman_name}
                    {s.country ? ` · ${s.country}` : ""}
                    {s.profession ? ` · ${s.profession}` : ""}
                  </p>
                  <p>{s.short_description}</p>
                </article>
              ))
            )
          ) : accounts === null ? (
            <p>ищем…</p>
          ) : accounts.length === 0 ? (
            <p>ничего не найдено</p>
          ) : (
            accounts.map((a) => (
              <article
                key={a.id}
                style={{ borderTop: "1px solid #ddd", paddingTop: "0.5rem" }}
              >
                <h3>
                  <Link href={`/u/${a.id}`} onClick={close}>
                    {a.display_name}
                  </Link>
                </h3>
                {a.badges.length > 0 ? (
                  <p>
                    {a.badges.map((b) => (
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
              </article>
            ))
          )}
        </Modal>
      ) : null}
    </section>
  );
}
