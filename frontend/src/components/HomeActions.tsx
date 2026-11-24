"use client";

import { useState } from "react";
import Link from "next/link";

import FavoriteButton from "./FavoriteButton";
import Modal from "./Modal";
import SearchSelect, { type SearchSelectOption } from "./SearchSelect";
import { apiFetch, type FullStory, type Recommendation } from "@/lib/home";

interface Props {
  options: {
    professions: SearchSelectOption[];
    fields: SearchSelectOption[];
    obstacleCategories: { id: number; name_ru: string; children: SearchSelectOption[] }[];
  };
  favoriteSlugs: string[];
}

type Mode = null | "worry" | "success" | "inspire";

const HELP_SKIP = [
  { key: "unknown", label: "не знаю, просто вдохнови меня" },
  { key: "absent", label: "тут пока нет моего ответа" },
] as const;

export default function HomeActions({ options, favoriteSlugs }: Props) {
  const [mode, setMode] = useState<Mode>(null);
  const [thinking, setThinking] = useState(false);
  const [result, setResult] = useState<Recommendation | null>(null);
  const [feedIndex, setFeedIndex] = useState(0);
  const [extraCommunity, setExtraCommunity] = useState<FullStory | null>(null);
  const [showRules, setShowRules] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ответы мастеров; переживаний можно выбрать несколько
  const [profession, setProfession] = useState<number | null>(null);
  const [field, setField] = useState<number | null>(null);
  const [obstacles, setObstacles] = useState<number[]>([]);
  const [step, setStep] = useState(0);
  const [alsoCommunity, setAlsoCommunity] = useState(true);
  const [openCategory, setOpenCategory] = useState<number | null>(null);

  // форма успеха
  const [storyTitle, setStoryTitle] = useState("");
  const [storyText, setStoryText] = useState("");
  const [publishConsent, setPublishConsent] = useState(false);

  function reset() {
    setMode(null);
    setStep(0);
    setProfession(null);
    setField(null);
    setObstacles([]);
    setAlsoCommunity(true);
    setOpenCategory(null);
    setThinking(false);
    setResult(null);
    setFeedIndex(0);
    setExtraCommunity(null);
    setShowRules(false);
    setError(null);
    setStoryTitle("");
    setStoryText("");
    setPublishConsent(false);
  }

  async function fetchRecommendation(
    params: Record<string, string | number | undefined | (string | number)[]>,
    withCommunity = false,
  ) {
    setThinking(true);
    setError(null);
    try {
      // небольшая пауза чтобы «думаю чем тебя поддержать» не мигала зря
      await new Promise((r) => setTimeout(r, 700));
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === null || v === "") continue;
        if (Array.isArray(v)) {
          for (const item of v) qs.append(k, String(item));
        } else {
          qs.set(k, String(v));
        }
      }
      const data = await apiFetch<Recommendation>(`/api/v1/recommendations?${qs.toString()}`);
      setResult(data);
      if (withCommunity) {
        const communityQs = new URLSearchParams(qs);
        communityQs.set("community_only", "true");
        const extra = await apiFetch<Recommendation>(`/api/v1/recommendations?${communityQs.toString()}`);
        setExtraCommunity(extra.story);
      }
      setThinking(false);
    } catch (e) {
      setError((e as Error).message);
      setThinking(false);
    }
  }

  async function inspireRandom() {
    setThinking(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 500));
      const data = await apiFetch<Recommendation>("/api/v1/stories/random");
      // единый формат ленты: одна случайная история без продолжения
      setResult(
        data.story
          ? { ...data, feed: [{ story: data.story, match_reasons: [], random: true }] }
          : data,
      );
      setThinking(false);
    } catch (e) {
      setError((e as Error).message);
      setThinking(false);
    }
  }

  async function submitSuccessStory() {
    setError(null);
    try {
      await apiFetch("/api/v1/stories/submit", {
        method: "POST",
        body: JSON.stringify({
          text: storyText,
          title: storyTitle || null,
          profession_tag_id: profession,
          field_tag_id: field,
          obstacle_tag_id: obstacles.length === 1 ? obstacles[0] : null,
          consent_publication: publishConsent,
        }),
      });
      reset();
      setToast("спасибо, что поделились! вы огромная молодец — модераторки проверят вашу историю как можно скорее");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const worrySteps = [
    {
      title: "что случилось, дорогая?",
      hint: "к какой сфере относится твоё сомнение? выбери профессию, если она тут есть",
      body: (
        <SearchSelect
          label="профессия"
          value={profession}
          onChange={setProfession}
          options={options.professions}
          placeholder="выбрать профессию"
        />
      ),
      canNext: true,
    },
    {
      title: "а по точнее?",
      hint: "в какой сфере ты сейчас?",
      body: (
        <SearchSelect
          label="сфера"
          value={field}
          onChange={setField}
          options={options.fields}
          placeholder="выбрать сферу"
        />
      ),
      canNext: true,
    },
    {
      title: "что тебя беспокоит?",
      hint: "раскрой категории и отметь всё, что отзывается — можно выбрать несколько",
      body: (
        <div>
          {options.obstacleCategories.map((cat) => (
            <div key={cat.id} style={{ marginBottom: "0.5rem" }}>
              <button
                type="button"
                onClick={() => setOpenCategory(openCategory === cat.id ? null : cat.id)}
                style={{ border: "1px solid #999", background: openCategory === cat.id ? "#eee" : "none", padding: "0.3rem 0.6rem", cursor: "pointer", width: "100%", textAlign: "left" }}
              >
                {openCategory === cat.id ? "▾ " : "▸ "}
                {cat.name_ru}
              </button>
              {openCategory === cat.id ? (
                <ul style={{ margin: "0.3rem 0 0 0", listStyle: "none", paddingLeft: "0.5rem" }}>
                  {cat.children.map((child) => (
                    <li key={child.id}>
                      <label style={{ display: "block" }}>
                        <input
                          type="checkbox"
                          checked={obstacles.includes(child.id)}
                          onChange={() => toggleObstacle(child.id)}
                        />{" "}
                        {child.name_ru}
                      </label>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
          <label style={{ display: "block" }}>
            <input
              type="checkbox"
              checked={alsoCommunity}
              onChange={(e) => setAlsoCommunity(e.target.checked)}
            />{" "}
            предложить также пользовательскую историю
          </label>
        </div>
      ),
      canNext: true,
    },
  ];

  const successSteps = [
    {
      title: "рады, что у вас что-то получилось!",
      hint: "скорее расскажите — в какой сфере вы добились успеха?",
      body: (
        <SearchSelect
          label="профессия"
          value={profession}
          onChange={setProfession}
          options={options.professions}
          placeholder="выбрать профессию"
        />
      ),
      canNext: true,
    },
    {
      title: "а по точнее?",
      hint: "в какой сфере случился успех?",
      body: (
        <SearchSelect
          label="сфера"
          value={field}
          onChange={setField}
          options={options.fields}
          placeholder="выбрать сферу"
        />
      ),
      canNext: true,
    },
    {
      title: "какие сомнения вы преодолели?",
      hint: "если подходящего нет — просто пропустите. можно отметить несколько",
      body: (
        <div>
          {options.obstacleCategories.map((cat) => (
            <div key={cat.id} style={{ marginBottom: "0.5rem" }}>
              <button
                type="button"
                onClick={() => setOpenCategory(openCategory === cat.id ? null : cat.id)}
                style={{ border: "1px solid #999", background: openCategory === cat.id ? "#eee" : "none", padding: "0.3rem 0.6rem", cursor: "pointer", width: "100%", textAlign: "left" }}
              >
                {openCategory === cat.id ? "▾ " : "▸ "}
                {cat.name_ru}
              </button>
              {openCategory === cat.id ? (
                <ul style={{ margin: "0.3rem 0 0 0", listStyle: "none", paddingLeft: "0.5rem" }}>
                  {cat.children.map((child) => (
                    <li key={child.id}>
                      <label style={{ display: "block" }}>
                        <input
                          type="checkbox"
                          checked={obstacles.includes(child.id)}
                          onChange={() => toggleObstacle(child.id)}
                        />{" "}
                        {child.name_ru}
                      </label>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </div>
      ),
      canNext: true,
    },
  ];

  function toggleObstacle(id: number) {
    setObstacles((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  const steps = mode === "worry" ? worrySteps : successSteps;
  // в мастере успеха шаг «рассказать» живёт отдельно от массива вопросов
  const isLast = mode === "worry" && step === worrySteps.length - 1;
  const writing = mode === "success" && step === 3;

  return (
    <>
      <nav>
        <ul style={{ listStyle: "none", padding: 0, display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <li>
            <button type="button" onClick={() => setMode("worry")}>
              поделиться переживанием
            </button>
          </li>
          <li>
            <button type="button" onClick={() => setMode("success")}>
              поделиться успехом
            </button>
          </li>
          <li>
            <button type="button" onClick={() => { setMode("inspire"); inspireRandom(); }}>
              вдохнови меня
            </button>
          </li>
        </ul>
      </nav>

      {toast ? (
        <p role="status" style={{ border: "1px solid #6a1b9a", padding: "0.5rem" }}>
          {toast}{" "}
          <button type="button" onClick={() => setToast(null)} aria-label="закрыть уведомление">
            ✕
          </button>
        </p>
      ) : null}

      {thinking ? (
        <Modal title="думаю, чем тебя поддержать…" onClose={reset}>
          <p>секундочку, подбираю историю…</p>
        </Modal>
      ) : null}

      {(mode === "worry" || (mode === "success" && !writing)) && steps[step] ? (
        <Modal title={steps[step].title} onClose={reset}>
          <p>{steps[step].hint}</p>
          {steps[step].body}
          {error ? <p>{error}</p> : null}
          <div style={{ marginTop: "0.75rem" }}>
            {step > 0 ? (
              <button type="button" onClick={() => setStep(step - 1)} style={{ marginRight: "0.4rem" }}>
                назад
              </button>
            ) : null}
            {!isLast && !(mode === "success" && step === 2) ? (
              <button type="button" onClick={() => setStep(step + 1)} style={{ marginRight: "0.4rem" }}>
                дальше
              </button>
            ) : mode === "worry" ? (
              <button
                type="button"
                onClick={() =>
                  fetchRecommendation(
                    {
                      profession: profession ?? undefined,
                      field: field ?? undefined,
                      obstacle: obstacles,
                    },
                    alsoCommunity,
                  )
                }
                style={{ marginRight: "0.4rem" }}
              >
                подобрать историю
              </button>
            ) : (
              <button type="button" onClick={() => setStep(3)} style={{ marginRight: "0.4rem" }}>
                рассказать историю
              </button>
            )}
            {mode === "success" && step < 2 ? (
              <button type="button" onClick={() => setStep(step + 1)} style={{ marginRight: "0.4rem" }}>
                пропустить вопрос
              </button>
            ) : null}
          </div>
          {mode === "worry" ? (
            <p>
              {HELP_SKIP.map((b) => (
                <button
                  key={b.key}
                  type="button"
                  onClick={() => fetchRecommendation({})}
                  style={{ display: "block", marginTop: "0.3rem", border: "none", background: "none", color: "#6a1b9a", cursor: "pointer", textDecoration: "underline", padding: 0 }}
                >
                  {b.label}
                </button>
              ))}
            </p>
          ) : null}
        </Modal>
      ) : null}

      {mode === "success" && writing ? (
        <Modal title="ваша история" onClose={reset}>
          <p>
            перед публикацией история пройдёт модерацию. мы проверяем что она{" "}
            <button
              type="button"
              onClick={() => setShowRules(!showRules)}
              style={{ border: "none", background: "none", color: "#6a1b9a", cursor: "pointer", textDecoration: "underline", padding: 0 }}
            >
              не нарушает правила
            </button>
          </p>
          {showRules ? (
            <RulesNote />
          ) : null}
          <label style={{ display: "block", marginTop: "0.5rem" }}>
            заголовок (необязательно):{" "}
            <input value={storyTitle} onChange={(e) => setStoryTitle(e.target.value)} maxLength={200} style={{ width: "100%" }} />
          </label>
          <label style={{ display: "block", marginTop: "0.5rem" }}>
            ваша история:
            <textarea
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
              rows={8}
              maxLength={15000}
              placeholder="расскажите как это было — своими словами, столько сколько нужно"
              style={{ width: "100%" }}
            />
          </label>
          {error ? <p>{error}</p> : null}
          <label style={{ display: "block", marginBottom: "0.5rem" }}>
            <input
              type="checkbox"
              checked={publishConsent}
              onChange={(e) => setPublishConsent(e.target.checked)}
            />{" "}
            я согласна на публикацию истории и на распространение указанных в
            ней сведений обо мне; права на историю остаются за мной
          </label>
          <button
            type="button"
            onClick={submitSuccessStory}
            disabled={storyText.trim().length === 0 || !publishConsent}
          >
            отправить
          </button>
        </Modal>
      ) : null}

      {result && !thinking ? (
        <Modal
          title={result.feed && result.feed[feedIndex] ? result.feed[feedIndex].story.title : "история"}
          onClose={reset}
        >
          {(() => {
            const current = result.feed?.[feedIndex];
            const next = result.feed?.[feedIndex + 1];
            const hasNext = Boolean(next);
            const nextIsInspiration = Boolean(next?.random);
            if (!current) {
              return <p>пока не нашлось подходящей истории, загляните в каталог позже</p>;
            }
            const s = current.story;
            return (
              <>
                <p>
                  {s.is_anonymous ? "имя скрыто" : s.woman_name}
                  {s.country ? ` · ${s.country}` : ""}
                  {s.profession ? ` · ${s.profession}` : ""}
                </p>
                {current.random || current.match_reasons.length === 0 ? (
                  <p>вот случайная история — вдруг она откликнется</p>
                ) : (
                  <p>
                    <b>почему эта история:</b>{" "}
                    {current.match_reasons
                      .map((r) => (r.tag ? `${r.text} «${r.tag}»` : r.text))
                      .join("; ")}
                  </p>
                )}
                {s.full_text.split(/\n{2,}/).map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
                <p>
                  <FavoriteButton
                    slug={s.slug}
                    initial={favoriteSlugs.includes(s.slug)}
                    canToggle={true}
                  />
                </p>
                <p>
                  <Link href={`/stories/${s.slug}`}>открыть целиком</Link>
                </p>
                <p style={{ color: "#666" }}>комментарии появятся позже</p>
                {extraCommunity && extraCommunity.slug !== s.slug ? (
                  <div style={{ borderTop: "1px dashed #999", marginTop: "0.75rem", paddingTop: "0.5rem" }}>
                    <h3>а вот ещё — живая история из сообщества</h3>
                    <p>
                      {extraCommunity.is_anonymous ? "имя скрыто" : extraCommunity.woman_name}
                      {extraCommunity.country ? ` · ${extraCommunity.country}` : ""}
                      {extraCommunity.profession ? ` · ${extraCommunity.profession}` : ""}
                    </p>
                    <p>{extraCommunity.short_description}</p>
                    <p>
                      <Link href={`/stories/${extraCommunity.slug}`}>прочитать целиком</Link>
                    </p>
                  </div>
                ) : null}
                <div style={{ marginTop: "0.75rem" }}>
                  {hasNext ? (
                    <>
                      {nextIsInspiration ? (
                        <p style={{ border: "1px dashed #999", padding: "0.4rem" }}>
                          по вашим ответам совпадений больше нет — дальше просто
                          вдохновляющие истории
                        </p>
                      ) : null}
                      <button type="button" onClick={() => setFeedIndex(feedIndex + 1)}>
                        ещё историю
                      </button>
                    </>
                  ) : (
                    <p>это всё, что мы пока нашли</p>
                  )}
                </div>
              </>
            );
          })()}
        </Modal>
      ) : null}
    </>
  );
}

function RulesNote() {
  return (
    <aside
      style={{
        border: "1px dashed #999",
        padding: "0.6rem",
        marginTop: "0.5rem",
        fontSize: "0.9rem",
      }}
    >
      <p style={{ marginTop: 0 }}>
        <b>правила сообщества</b>
      </p>
      <ul style={{ marginBottom: 0 }}>
        <li>
          если в истории тяжёлые темы — поставьте предупреждение в начале текста
          (триггер-варнинг), чтобы другие читательницы были готовы
        </li>
        <li>без оскорблений, мизогинии и травли — в любую сторону</li>
        <li>
          просим не приукрашивать: любая победа важна, даже маленькая, ей не нужны
          украшательства
        </li>
        <li>без личных данных (своих и чужих) и ссылок на сторонние соцсети</li>
        <li>история должна быть вашей — не пересказ чужой жизни без согласия</li>
      </ul>
    </aside>
  );
}
