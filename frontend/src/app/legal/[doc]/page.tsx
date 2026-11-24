import Link from "next/link";
import { notFound } from "next/navigation";

import SiteHeader from "@/components/SiteHeader";
import { LEGAL_DOCS, getLegalDoc } from "@/lib/legal-docs";

export function generateStaticParams() {
  return LEGAL_DOCS.map((doc) => ({ doc: doc.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ doc: string }> }) {
  const { doc: slug } = await params;
  const doc = getLegalDoc(slug);
  return { title: doc ? `${doc.title} — не первая` : "документ — не первая" };
}

export default async function LegalDocPage({ params }: { params: Promise<{ doc: string }> }) {
  const { doc: slug } = await params;
  const doc = getLegalDoc(slug);
  if (!doc) notFound();

  return (
    <>
      <SiteHeader />
      <main>
        <h1>{doc.title}</h1>
        <p>редакция от {doc.updated}</p>
        {doc.sections.map((section) => (
          <section key={section.h}>
            <h2>{section.h}</h2>
            {section.p.map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </section>
        ))}
        <p>
          <Link href="/legal">← все документы</Link>
        </p>
      </main>
    </>
  );
}
