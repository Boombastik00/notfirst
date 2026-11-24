"use client";

import { useState } from "react";
import Link from "next/link";

// старт входа всегда на том же хосте что и возврат из google иначе
// сессионная cookie с state не доедет до коллбека (127.0.0.1 и localhost — разные хосты)
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default function LoginPage() {
  const [showConsent, setShowConsent] = useState(false);
  const [agreedTerms, setAgreedTerms] = useState(false);
  const [agreedPd, setAgreedPd] = useState(false);
  const [confirmedAge, setConfirmedAge] = useState(false);

  const allAgreed = agreedTerms && agreedPd && confirmedAge;

  if (!showConsent) {
    return (
      <main>
        <h1>вход</h1>
        <p>войти через google-аккаунт</p>
        <button type="button" onClick={() => setShowConsent(true)}>
          продолжить с google
        </button>
        <p>
          <Link href="/">вернуться на главную</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <h1>согласия для регистрации</h1>

      <label style={{ display: "block" }}>
        <input
          type="checkbox"
          checked={agreedTerms}
          onChange={(e) => setAgreedTerms(e.target.checked)}
        />{" "}
        я принимаю{" "}
        <Link href="/legal/terms">пользовательское соглашение</Link> и{" "}
        <Link href="/legal/community-rules">правила сообщества</Link>
      </label>

      <label style={{ display: "block" }}>
        <input
          type="checkbox"
          checked={agreedPd}
          onChange={(e) => setAgreedPd(e.target.checked)}
        />{" "}
        я даю{" "}
        <Link href="/legal/privacy">согласие на обработку персональных данных</Link>{" "}
        (id аккаунта, email, имя и изображение профиля)
      </label>

      <label style={{ display: "block" }}>
        <input
          type="checkbox"
          checked={confirmedAge}
          onChange={(e) => setConfirmedAge(e.target.checked)}
        />{" "}
        мне 12 лет или больше. если мне меньше 18 — мой законный представитель
        (родитель или опекун) знает об использовании платформы и не против
      </label>

      <div>
        {allAgreed ? (
          <a href={`${SITE_URL}/api/v1/auth/google/start?consent=2026-11-24`}>
            согласна, продолжить вход
          </a>
        ) : (
          <span>отметьте все пункты чтобы продолжить</span>
        )}
      </div>

      <p>
        <button type="button" onClick={() => setShowConsent(false)}>
          назад
        </button>
      </p>
    </main>
  );
}
