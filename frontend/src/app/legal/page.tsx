import Link from "next/link";

import SiteHeader from "@/components/SiteHeader";
import { LEGAL_DOCS } from "@/lib/legal-docs";

export const metadata = { title: "правовые документы — не первая" };

export default function LegalIndexPage() {
  return (
    <>
      <SiteHeader />
      <main>
        <h1>правовые документы</h1>
        <ul>
          {LEGAL_DOCS.map((doc) => (
            <li key={doc.slug}>
              <Link href={`/legal/${doc.slug}`}>{doc.title}</Link>
            </li>
          ))}
        </ul>
        <p>
          <Link href="/">← на главную</Link>
        </p>
      </main>
    </>
  );
}
