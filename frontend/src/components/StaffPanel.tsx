"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/api";

interface BadgeItem {
  code: string;
  label: string;
}

// панель для модераторш: выдача префиксов и баны
export default function StaffPanel({
  userId,
  displayName,
  catalog,
  currentBadges,
  isBanned,
}: {
  userId: string;
  displayName: string;
  catalog: BadgeItem[];
  currentBadges: string[];
  isBanned: boolean;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [badges, setBadges] = useState<string[]>(currentBadges);
  const [banned, setBanned] = useState(isBanned);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function toggleBadge(code: string) {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      const has = badges.includes(code);
      if (has) {
        await apiFetch(`/api/v1/u/${userId}/badges/${code}`, { method: "DELETE" });
        setBadges(badges.filter((b) => b !== code));
        setNotice("префикс снят");
      } else {
        await apiFetch(`/api/v1/u/${userId}/badges`, {
          method: "POST",
          body: JSON.stringify({ badge: code }),
        });
        setBadges([...badges, code]);
        setNotice("префикс выдан");
      }
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleBan() {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      if (banned) {
        await apiFetch(`/api/v1/u/${userId}/ban`, { method: "DELETE" });
        setBanned(false);
        setNotice(`${displayName} разблокирована`);
      } else {
        await apiFetch(`/api/v1/u/${userId}/ban`, { method: "POST" });
        setBanned(true);
        setNotice(`${displayName} заблокирована`);
      }
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section style={{ border: "1px solid #bbb", padding: "0.5rem" }}>
      <p>
        <button type="button" disabled={busy} onClick={() => setOpen(!open)}>
          {open ? "×" : "+"} префиксы
        </button>{" "}
        <button type="button" disabled={busy} onClick={toggleBan}>
          {banned ? "разблокировать" : "заблокировать"}
        </button>
      </p>

      {open ? (
        <ul style={{ listStyle: "none", paddingLeft: 0 }}>
          {catalog.map((b) => {
            const has = badges.includes(b.code);
            return (
              <li key={b.code}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => toggleBadge(b.code)}
                  style={{ marginRight: "0.4rem" }}
                >
                  {has ? "✓" : "+"} {b.label}
                </button>
                {has ? <span>(выдан)</span> : null}
              </li>
            );
          })}
        </ul>
      ) : null}

      {notice ? <p role="status">{notice}</p> : null}
      {error ? <p>{error}</p> : null}
    </section>
  );
}
