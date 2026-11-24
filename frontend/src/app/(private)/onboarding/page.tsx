"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import SearchSelect from "@/components/SearchSelect";
import { apiFetch, type OnboardingInfo } from "@/lib/api";

// темы и сомнения тут сознательно не спрашиваем: темы живут в профиле,
// сомнения выбираются в «поделиться переживанием» на главной
const STEPS = [
  { title: "сколько тебе лет?", hint: "нужна только категория, точную дату рождения мы не спрашиваем" },
  { title: "где ты живёшь?", hint: "можно не указывать, можно печатать чтобы найти" },
  { title: "кем работаешь?", hint: "можно не указывать, можно печатать чтобы найти" },
  { title: "что тебе интересно?", hint: "отметь сферы, которые тебе близки, или пропусти шаг" },
] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [data, setData] = useState<OnboardingInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);

  const [ageId, setAgeId] = useState<number | null>(null);
  const [parentAgreed, setParentAgreed] = useState(false);
  const [countryId, setCountryId] = useState<number | null>(null);
  const [professionId, setProfessionId] = useState<number | null>(null);
  const [interests, setInterests] = useState<number[]>([]);

  useEffect(() => {
    apiFetch<OnboardingInfo>("/api/v1/onboarding")
      .then((info) => {
        setData(info);
        setAgeId(info.current.age_tag_id);
        setCountryId(info.current.country_tag_id);
        setProfessionId(info.current.profession_tag_id);
        setInterests(info.current.interest_tag_ids);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  async function finish(skip = false) {
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/api/v1/onboarding", {
        method: "POST",
        body: JSON.stringify(
          skip
            ? { skip: true }
            : {
                age_tag_id: ageId,
                country_tag_id: countryId,
                profession_tag_id: professionId,
                interest_tag_ids: interests,
                parent_confirmed: parentAgreed,
              },
        ),
      });
      router.push("/");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  if (error && !data) {
    return (
      <main>
        <h1>анкета</h1>
        <p>{error}</p>
      </main>
    );
  }
  if (!data) {
    return (
      <main>
        <h1>анкета</h1>
        <p>загружаем…</p>
      </main>
    );
  }

  function toggleInterest(id: number) {
    setInterests((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  const isLast = step === STEPS.length - 1;
  const ageSelected = data.options.age_categories.find((t) => t.id === ageId);
  const needParent = ageSelected?.slug === "under-18";
  const canNext = step !== 0 || (ageId !== null && (!needParent || parentAgreed));

  return (
    <main>
      <h1>расскажи о себе</h1>
      <p>
        шаг {step + 1} из {STEPS.length}
      </p>

      <fieldset>
        <legend>
          <b>{STEPS[step].title}</b>
        </legend>
        <p>{STEPS[step].hint}</p>

        {step === 0 ? (
          <>
            {data.options.age_categories.map((tag) => (
              <label key={tag.id} style={{ display: "block" }}>
                <input
                  type="radio"
                  name="age"
                  checked={ageId === tag.id}
                  onChange={() => setAgeId(tag.id)}
                />{" "}
                {tag.name_ru}
              </label>
            ))}
            {data.options.age_categories.find((t) => t.id === ageId)?.slug === "under-18" ? (
              <p>
                <label style={{ display: "block", border: "1px dashed #999", padding: "0.5rem" }}>
                  <input
                    type="checkbox"
                    checked={parentAgreed}
                    onChange={(e) => setParentAgreed(e.target.checked)}
                  />{" "}
                  мой законный представитель (родитель или опекун) знает о моей
                  регистрации и согласен на обработку моих персональных данных
                </label>
              </p>
            ) : null}
          </>
        ) : null}

        {step === 1 ? (
          <SearchSelect
            label="страна"
            value={countryId}
            onChange={setCountryId}
            options={data.options.countries}
            placeholder="выбрать страну"
          />
        ) : null}

        {step === 2 ? (
          <SearchSelect
            label="профессия"
            value={professionId}
            onChange={setProfessionId}
            options={data.options.professions}
            placeholder="выбрать профессию"
          />
        ) : null}

        {step === 3
          ? data.options.fields.map((tag) => (
              <label key={tag.id} style={{ display: "block" }}>
                <input
                  type="checkbox"
                  checked={interests.includes(tag.id)}
                  onChange={() => toggleInterest(tag.id)}
                />{" "}
                {tag.name_ru}
              </label>
            ))
          : null}
      </fieldset>

      {error ? <p>{error}</p> : null}

      <nav>
        {step > 0 ? <button onClick={() => setStep(step - 1)}>назад</button> : null}{" "}
        {!isLast ? (
          <button disabled={!canNext} onClick={() => setStep(step + 1)}>
            дальше
          </button>
        ) : (
          <button disabled={busy || !canNext} onClick={() => finish(false)}>
            готово
          </button>
        )}{" "}
        <button disabled={busy} onClick={() => finish(true)}>
          заполнить позже
        </button>
      </nav>

      <p>
        <Link href="/">на главную</Link>
      </p>
    </main>
  );
}
