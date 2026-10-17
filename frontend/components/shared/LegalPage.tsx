import Link from "next/link";
import { ArrowLeft, Shield } from "lucide-react";

export interface LegalSection {
  heading: string;
  body: React.ReactNode;
}

/** A plain readable page for the terms and the privacy notice. */
export function LegalPage({ title, updated, intro, sections }: { title: string; updated: string; intro: string; sections: LegalSection[] }) {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-4 py-10 sm:px-6">
      <Link href="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to Home
      </Link>
      <div className="mt-6 flex items-center gap-3">
        <Shield className="h-6 w-6 text-primary" aria-hidden="true" />
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">Last updated {updated}</p>
      <p className="mt-6 leading-relaxed">{intro}</p>
      {sections.map((s) => (
        <section key={s.heading} className="mt-8">
          <h2 className="text-lg font-semibold">{s.heading}</h2>
          <div className="mt-2 space-y-3 leading-relaxed text-foreground/90">{s.body}</div>
        </section>
      ))}
      <nav className="mt-12 flex gap-4 border-t pt-6 text-sm text-muted-foreground" aria-label="Legal pages">
        <Link href="/terms" className="hover:text-foreground hover:underline">Terms of use</Link>
        <Link href="/privacy" className="hover:text-foreground hover:underline">Privacy notice</Link>
      </nav>
    </main>
  );
}
