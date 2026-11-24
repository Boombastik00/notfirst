"use client";

import { useEffect, useRef, useState } from "react";

export interface SearchSelectOption {
  id: number;
  name_ru: string;
}

// компактный комбобокс: список прячется и выходит маленьким окошком
// только по клику, печатать можно чтобы отфильтровать
export default function SearchSelect({
  label,
  value,
  onChange,
  options,
  placeholder = "выбрать",
}: {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
  options: SearchSelectOption[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = options.find((o) => o.id === value) ?? null;

  // клик мимо закрывает окошко
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const filtered =
    query.trim() !== ""
      ? options.filter((o) => o.name_ru.toLowerCase().includes(query.trim().toLowerCase()))
      : options;

  const shown = open && query !== "" ? query : selected ? selected.name_ru : "";

  return (
    <div ref={rootRef} style={{ position: "relative", display: "inline-block" }}>
      <label>
        {label}:{" "}
        <input
          type="text"
          value={shown}
          placeholder={placeholder}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            // закрываем с задержкой чтобы успел отработать клик по варианту
            window.setTimeout(() => {
              setOpen(false);
              setQuery("");
            }, 120);
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            if (value !== null) onChange(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
              setQuery("");
            }
          }}
          style={{ width: "12rem" }}
        />
      </label>{" "}
      <button
        type="button"
        aria-label={open ? "закрыть список" : "открыть список"}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => {
          setOpen((v) => !v);
          setQuery("");
        }}
        style={{ border: "none", background: "none", cursor: "pointer" }}
      >
        {open ? "▴" : "▾"}
      </button>

      {open ? (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            zIndex: 10,
            maxHeight: "10rem",
            overflowY: "auto",
            background: "#fff",
            border: "1px solid #999",
            minWidth: "12rem",
          }}
        >
          {selected ? (
            <button
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(null);
                setQuery("");
              }}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                border: "none",
                background: "none",
                padding: "0.15rem 0.4rem",
                cursor: "pointer",
                fontStyle: "italic",
              }}
            >
              снять выбор
            </button>
          ) : null}
          {filtered.map((o) => (
            <button
              key={o.id}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(o.id);
                setQuery("");
                setOpen(false);
              }}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                border: "none",
                background: value === o.id ? "#eee" : "none",
                padding: "0.15rem 0.4rem",
                cursor: "pointer",
              }}
            >
              {o.name_ru}
            </button>
          ))}
          {filtered.length === 0 ? (
            <p style={{ margin: 0, padding: "0.15rem 0.4rem" }}>ничего не нашлось</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
