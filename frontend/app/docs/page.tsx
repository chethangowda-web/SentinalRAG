import type { Metadata } from "next";
import { Shield, BookOpen, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Documentation",
  description: "SentinelRAG documentation and API reference.",
};

const sections = [
  {
    title: "Getting Started",
    description: "Quick start guide, installation, and configuration.",
    links: [
      { href: "https://github.com/chethangowda-web/SentinalRAG#readme", label: "README" },
      { href: "https://github.com/chethangowda-web/SentinalRAG", label: "GitHub" },
    ],
  },
  {
    title: "API Reference",
    description: "Complete API documentation with examples.",
    links: [
      { href: "/docs", label: "Swagger UI" },
      { href: "/openapi.json", label: "OpenAPI JSON" },
    ],
  },
  {
    title: "Architecture",
    description: "System architecture, components, and data flow.",
    links: [
      { href: "https://github.com/chethangowda-web/SentinalRAG?tab=readme-ov-file#architecture-overview", label: "Architecture Overview" },
    ],
  },
];

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Documentation</h1>
            <p className="text-muted-foreground">Learn how to use and deploy SentinelRAG.</p>
          </div>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {sections.map((section) => (
            <div
              key={section.title}
              className="rounded-xl border bg-card p-6 transition-all duration-200 hover:shadow-md"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 mb-4">
                <BookOpen className="h-5 w-5 text-primary" />
              </div>
              <h2 className="font-semibold mb-2">{section.title}</h2>
              <p className="text-sm text-muted-foreground mb-4">{section.description}</p>
              <div className="space-y-2">
                {section.links.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    target={link.href.startsWith("http") ? "_blank" : undefined}
                    rel={link.href.startsWith("http") ? "noreferrer" : undefined}
                    className="flex items-center gap-2 text-sm text-primary hover:underline"
                  >
                    <ArrowRight className="h-3.5 w-3.5" />
                    {link.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <p className="text-sm text-muted-foreground mb-4">
            Want to see the full API in action?
          </p>
          <Button asChild>
            <Link href="/dashboard">Go to Dashboard</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
