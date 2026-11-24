"use client";

import type { ReactNode } from "react";

// окно в окне: страница темнеет, поверх выпадает панель
export default function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
        zIndex: 100,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#fff",
          maxWidth: "34rem",
          width: "100%",
          maxHeight: "85vh",
          overflowY: "auto",
          padding: "1.25rem",
          position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          aria-label="закрыть"
          onClick={onClose}
          style={{ position: "absolute", top: "0.5rem", right: "0.75rem", border: "none", background: "none", fontSize: "1.2rem", cursor: "pointer" }}
        >
          ✕
        </button>
        <h2 style={{ marginTop: 0 }}>{title}</h2>
        {children}
      </div>
    </div>
  );
}
