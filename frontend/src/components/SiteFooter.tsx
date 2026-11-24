import Link from "next/link";

const LINKS = [
  { href: "/legal/terms", label: "пользовательское соглашение" },
  { href: "/legal/privacy", label: "обработка данных" },
  { href: "/legal/community-rules", label: "правила сообщества" },
  { href: "/legal/cookies", label: "cookies" },
  { href: "/legal/content-license", label: "лицензия на истории" },
  { href: "/legal/moderation", label: "модерация" },
  { href: "/legal/data-deletion", label: "удаление данных" },
  { href: "/legal/contacts", label: "контакты" },
];

export default function SiteFooter() {
  return (
    <footer>
      <nav>
        <ul>
          {LINKS.map((link) => (
            <li key={link.href} style={{ display: "inline-block", marginRight: "0.75rem" }}>
              <Link href={link.href}>{link.label}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <p>12+ · «не первая», открытый волонтёрский проект</p>
    </footer>
  );
}
