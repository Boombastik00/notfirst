"use client";

import { useState } from "react";
import Link from "next/link";

import { apiFetch } from "@/lib/api";

interface SourceRow {
  title: string;
  url: string;
}

// окно «истории»: написание официальных историй с обязательными источниками
export default function WritePage() {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [sources, setSources] = useState<SourceRow[]>([{ title: "", url: "" }]);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function setSource(i: number, patch: Partial<SourceRow>) {
    setSources((prev) => prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  }

  function addSource() {
    setSources((prev) => [...prev, { title: "", url: "" }]);
  }

  function removeSource(i: number) {
    setSources((prev) => (prev.length <= 1 ? prev : prev.filter((_, idx) => idx !== i)));
  }

  async function submit() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch("/api/v1/stories/official", {
        method: "POST",
        body: JSON.stringify({
          title,
          text,
          sources: sources
            .filter((s) => s.title.trim() || s.url.trim())
            .map((s) => ({ title: s.title.trim(), url: s.url.trim() || null })),
        }),
      });
      setNotice("история отправлена на модерацию");
      setTitle("");
      setText("");
      setSources([{ title: "", url: "" }]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const canSubmit = !busy && title.trim().length > 0 && text.trim().length >= 200;

  return (
    <main>
      <h1>официальная история</h1>
      <p>
        такие истории — проверенные биографии: у каждой обязателен хотя бы один источник,
        после отправки их смотрит модераторша
      </p>

      {notice ? <p role="status">{notice}</p> : null}
      {error ? <p>{error}</p> : null}

      <label style={{ display: "block" }}>
        заголовок:{" "}
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          placeholder="о ком эта история"
        />
      </label>

      <label style={{ display: "block" }}>
        текст:{" "}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={12}
          maxLength={50000}
          placeholder="подробная история, от 200 символов"
        />
      </label>
      {text.trim().length > 0 && text.trim().length < 200 ? (
        <p>нужно ещё хотя бы {200 - text.trim().length} символов</p>
      ) : null}

      <fieldset>
        <legend>источники (обязательно)</legend>
        {sources.map((s, i) => (
          <div key={i} style={{ marginBottom: "0.4rem" }}>
            <input
              value={s.title}
              onChange={(e) => setSource(i, { title: e.target.value })}
              maxLength={300}
              placeholder={i === 0 ? "название источника" : "ещё один источник"}
              aria-label={`название источника ${i + 1}`}
            />{" "}
            <input
              value={s.url}
              onChange={(e) => setSource(i, { url: e.target.value })}
              maxLength={1000}
              placeholder="ссылка (необязательно)"
              aria-label={`ссылка источника ${i + 1}`}
            />
            {sources.length > 1 ? (
              <button type="button" onClick={() => removeSource(i)} aria-label="убрать источник">
                ×
              </button>
            ) : null}
          </div>
        ))}
        <p>
          <button type="button" onClick={addSource}>
            + источник
          </button>
        </p>
      </fieldset>

      <button disabled={!canSubmit} onClick={submit}>
        отправить
      </button>

      <p>
        <Link href="/">← на главную</Link>
      </p>
    </main>
  );
}
