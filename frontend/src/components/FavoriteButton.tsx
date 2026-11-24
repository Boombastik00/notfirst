"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

// сердечко на карточке и странице истории
// начальное состояние приходит с сервера чтобы не мигало после загрузки
export default function FavoriteButton({
  slug,
  initial,
  canToggle,
}: {
  slug: string;
  initial: boolean;
  canToggle: boolean;
}) {
  const router = useRouter();
  const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false);

  if (!canToggle) {
    return null;
  }

  async function toggle() {
    setBusy(true);
    try {
      const resp = await fetch(`/api/v1/favorites/${slug}`, {
        method: saved ? "DELETE" : "PUT",
      });
      if (resp.ok) {
        setSaved(!saved);
        router.refresh();
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={busy}
      aria-pressed={saved}
      title={saved ? "убрать из сохранённых" : "сохранить историю"}
    >
      {saved ? "♥ в сохранённых" : "♡ сохранить"}
    </button>
  );
}
