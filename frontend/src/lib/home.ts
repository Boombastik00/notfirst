// типы для окна истории из подбора
export interface FullStory {
  slug: string;
  title: string;
  woman_name: string;
  short_description: string;
  full_text: string;
  story_type: string;
  is_anonymous: boolean;
  country: string | null;
  profession: string | null;
}

export interface MatchReason {
  dimension: string;
  text: string;
  tag: string | null;
}

export interface FeedItem {
  story: FullStory;
  match_reasons: MatchReason[];
  random: boolean;
}

export interface Recommendation {
  story: FullStory | null;
  match_reasons: MatchReason[];
  random: boolean;
  feed?: FeedItem[];
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!resp.ok) {
    let detail = `ошибка ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // не json, оставим код
    }
    throw new Error(detail);
  }
  if (resp.status === 204 || resp.status === 202) return undefined as T;
  return (await resp.json()) as T;
}
