// минимальный ходок в api: same-origin значит cookie уходят сами
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
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export interface MeInfo {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  onboarding_completed: boolean;
  has_rejection_notice: boolean;
}

export interface TagInfo {
  id: number;
  group_code: string;
  parent_id: number | null;
  slug: string;
  name_ru: string;
}

export interface OnboardingInfo {
  already_completed: boolean;
  options: {
    age_categories: TagInfo[];
    countries: TagInfo[];
    professions: TagInfo[];
    fields: TagInfo[];
    themes: TagInfo[];
  };
  current: {
    age_tag_id: number | null;
    country_tag_id: number | null;
    profession_tag_id: number | null;
    current_field_tag_id: number | null;
    interest_tag_ids: number[];
  };
}

export interface ProfileInfo {
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  age: TagInfo | null;
  country: TagInfo | null;
  profession: TagInfo | null;
  current_field: TagInfo | null;
  interests: TagInfo[];
  onboarding_completed: boolean;
}
