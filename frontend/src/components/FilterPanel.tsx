"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import SearchSelect, { type SearchSelectOption } from "./SearchSelect";

export interface FilterGroups {
  countries: SearchSelectOption[];
  professions: SearchSelectOption[];
  fields: SearchSelectOption[];
  obstacles: SearchSelectOption[];
  themes: SearchSelectOption[];
}

const TYPE_LABELS: Record<string, string> = {
  verified_biography: "проверенная биография",
  community_story: "история сообщества",
};

const CATALOG_SORTS = [
  { value: "new", label: "сначала новые" },
  { value: "old", label: "сначала старые" },
  { value: "title", label: "по заголовку" },
];

// фильтры живут в локальном состоянии и уходят в адрес только по кнопке «найти»
// поэтому список не выпадает пока пользовательница сама не попросит
export default function FilterPanel({
  options,
  initial,
  basePath = "/catalog",
  useShow = true,
  sortVariants = CATALOG_SORTS,
}: {
  options: FilterGroups;
  initial: {
    q: string;
    country: number | null;
    profession: number | null;
    field: number | null;
    obstacle: number | null;
    theme: number | null;
    story_type: string;
    sort: string;
  };
  basePath?: string;
  useShow?: boolean;
  sortVariants?: { value: string; label: string }[];
}) {
  const router = useRouter();
  const [q, setQ] = useState(initial.q);
  const [country, setCountry] = useState(initial.country);
  const [profession, setProfession] = useState(initial.profession);
  const [field, setField] = useState(initial.field);
  const [obstacle, setObstacle] = useState(initial.obstacle);
  const [theme, setTheme] = useState(initial.theme);
  const [storyType, setStoryType] = useState(initial.story_type);
  const [sort, setSort] = useState(initial.sort);

  function search() {
    const qs = new URLSearchParams();
    if (q.trim()) qs.set("q", q.trim());
    if (country) qs.set("country", String(country));
    if (profession) qs.set("profession", String(profession));
    if (field) qs.set("field", String(field));
    if (obstacle) qs.set("obstacle", String(obstacle));
    if (theme) qs.set("theme", String(theme));
    if (storyType) qs.set("story_type", storyType);
    if (sort && sort !== sortVariants[0]?.value) qs.set("sort", sort);
    if (useShow) qs.set("show", "1");
    router.push(`${basePath}?${qs.toString()}`);
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        search();
      }}
    >
      <fieldset>
        <legend>фильтры</legend>

        <label>
          поиск:{" "}
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            maxLength={100}
            placeholder="имя героини или слово"
            style={{ width: "12rem" }}
          />
        </label>

        <div>
          <SearchSelect
            label="страна"
            value={country}
            onChange={setCountry}
            options={options.countries}
            placeholder="все страны"
          />
        </div>

        <div>
          <SearchSelect
            label="профессия"
            value={profession}
            onChange={setProfession}
            options={options.professions}
            placeholder="все профессии"
          />
        </div>

        <div>
          <SearchSelect
            label="сфера"
            value={field}
            onChange={setField}
            options={options.fields}
            placeholder="все сферы"
          />
        </div>

        <div>
          <SearchSelect
            label="сомнение"
            value={obstacle}
            onChange={setObstacle}
            options={options.obstacles}
            placeholder="все сомнения"
          />
        </div>

        <div>
          <SearchSelect
            label="тема"
            value={theme}
            onChange={setTheme}
            options={options.themes}
            placeholder="все темы"
          />
        </div>

        <label>
          тип:{" "}
          <select value={storyType} onChange={(e) => setStoryType(e.target.value)}>
            <option value="">любой</option>
            {Object.entries(TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label>
          сортировка:{" "}
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            {sortVariants.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>

        <p>
          <button type="submit">найти истории</button>{" "}
          <Link href={basePath}>сбросить</Link>
        </p>
      </fieldset>
    </form>
  );
}
