"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import MyStories from "@/components/MyStories";
import SearchSelect from "@/components/SearchSelect";
import { apiFetch, type MeInfo, type OnboardingInfo, type ProfileInfo, type TagInfo } from "@/lib/api";

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<ProfileInfo | null>(null);
  const [options, setOptions] = useState<OnboardingInfo["options"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [ageId, setAgeId] = useState<number | null>(null);
  const [countryId, setCountryId] = useState<number | null>(null);
  const [professionId, setProfessionId] = useState<number | null>(null);
  const [fieldId, setFieldId] = useState<number | null>(null);
  const [interests, setInterests] = useState<number[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [rejectionNotice, setRejectionNotice] = useState(false);
  const [badges, setBadges] = useState<{ code: string; label: string }[]>([]);

  useEffect(() => {
    Promise.all([
      apiFetch<ProfileInfo>("/api/v1/profile"),
      apiFetch<OnboardingInfo>("/api/v1/onboarding"),
    ])
      .then(([p, o]) => {
        setProfile(p);
        setOptions(o.options);
        setName(p.display_name ?? "");
        setBio(p.bio ?? "");
        setAgeId(p.age?.id ?? null);
        setCountryId(p.country?.id ?? null);
        setProfessionId(p.profession?.id ?? null);
        setFieldId(p.current_field?.id ?? null);
        setInterests(p.interests.map((t) => t.id));
      })
      .catch((e: Error) => setError(e.message));

    // одноразовое уведомление об отклонённой истории, см шапку с восклицательным знаком
    apiFetch<MeInfo>("/api/v1/auth/me")
      .then((me) => {
        setRejectionNotice(me.has_rejection_notice);
        // свои префиксы берём из публичного профиля
        return apiFetch<{ badges: { code: string; label: string }[] }>(`/api/v1/u/${me.id}`);
      })
      .then((p) => setBadges(p.badges ?? []))
      .catch(() => setRejectionNotice(false));
  }, []);

  async function dismissRejection() {
    setRejectionNotice(false);
    await fetch("/api/v1/profile/acknowledge-rejection", { method: "POST" });
    router.refresh();
  }

  async function save() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch("/api/v1/profile", {
        method: "PATCH",
        body: JSON.stringify({
          display_name: name || null,
          bio: bio || null,
          age_tag_id: ageId,
          country_tag_id: countryId,
          profession_tag_id: professionId,
          current_field_tag_id: fieldId,
        }),
      });
      await apiFetch("/api/v1/profile/tags", {
        method: "PUT",
        body: JSON.stringify({ tag_ids: interests }),
      });
      setNotice("сохранено");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function removeAccount() {
    setBusy(true);
    try {
      await apiFetch("/api/v1/account/delete", { method: "POST" });
      router.push("/");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  if (error && !profile) {
    return (
      <main>
        <h1>профиль</h1>
        <p>{error}</p>
      </main>
    );
  }
  if (!profile || !options) {
    return (
      <main>
        <h1>профиль</h1>
        <p>загружаем…</p>
      </main>
    );
  }

  function toggleInterest(id: number) {
    setInterests((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  return (
    <main>
      <h1>профиль</h1>
      {badges.length > 0 ? (
        <p>
          {badges.map((b) => (
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
      {rejectionNotice ? (
        <p role="status" style={{ border: "1px solid #b00020", padding: "0.5rem" }}>
          к сожалению, одна из ваших историй не прошла модерацию :(
          <button type="button" onClick={dismissRejection} style={{ marginLeft: "0.5rem" }}>
            понятно
          </button>
        </p>
      ) : null}
      <p>email: {profile.email}</p>

      <label style={{ display: "block" }}>
        имя:{" "}
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={100} />
      </label>

      <label style={{ display: "block" }}>
        возрастная категория:{" "}
        <select
          value={ageId ?? ""}
          onChange={(e) => setAgeId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">не указано</option>
          {options.age_categories.map((tag: TagInfo) => (
            <option key={tag.id} value={tag.id}>
              {tag.name_ru}
            </option>
          ))}
        </select>
      </label>

      <SearchSelect
        label="страна"
        value={countryId}
        onChange={setCountryId}
        options={options.countries}
        placeholder="выбрать страну"
      />

      <SearchSelect
        label="профессия"
        value={professionId}
        onChange={setProfessionId}
        options={options.professions}
        placeholder="выбрать профессию"
      />

      <details>
        <summary>дополнительная информация (необязательно)</summary>

        <SearchSelect
          label="сфера деятельности"
          value={fieldId}
          onChange={setFieldId}
          options={options.fields}
          placeholder="выбрать сферу"
        />

        <fieldset>
          <legend>темы</legend>
          {options.themes.map((tag: TagInfo) => (
            <label key={tag.id} style={{ display: "block" }}>
              <input
                type="checkbox"
                checked={interests.includes(tag.id)}
                onChange={() => toggleInterest(tag.id)}
              />{" "}
              {tag.name_ru}
            </label>
          ))}
        </fieldset>

        <label style={{ display: "block" }}>
          о себе:{" "}
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={1000}
            rows={4}
            placeholder="пара слов о себе, увидят другие пользовательницы когда появится коммьюнити"
          />
        </label>
      </details>

      <MyStories />

      {notice ? <p>{notice}</p> : null}
      {error ? <p>{error}</p> : null}

      <button disabled={busy} onClick={save}>
        сохранить
      </button>

      <fieldset>
        <legend>удаление аккаунта</legend>
        <p>
          аккаунт удаляется вместе с профилем, интересами, избранным и сессиями.
          это действие нельзя отменить.
        </p>
        {confirmDelete ? (
          <>
            <button disabled={busy} onClick={removeAccount}>
              да, удалить аккаунт навсегда
            </button>{" "}
            <button onClick={() => setConfirmDelete(false)}>отмена</button>
          </>
        ) : (
          <button onClick={() => setConfirmDelete(true)}>удалить аккаунт</button>
        )}
      </fieldset>

      <p>
        <Link href="/">на главную</Link>
      </p>
    </main>
  );
}
