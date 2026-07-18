"use client";

const layers = [
  {
    title: "Presentation Layer",
    items: ["Next.js 15 Frontend", "Tailwind CSS / shadcn/ui", "REST API Client"],
  },
  {
    title: "API Gateway",
    items: ["FastAPI Backend", "Pydantic Validation", "Rate Limiting"],
  },
  {
    title: "Application Layer",
    items: ["OCR Pipeline", "Hybrid Retrieval", "Self-Correction Engine", "LangGraph Orchestration"],
  },
  {
    title: "Data Layer",
    items: ["PostgreSQL", "Qdrant Vector DB", "Redis Cache"],
  },
  {
    title: "Infrastructure",
    items: ["Docker Compose", "CI/CD Pipeline", "Monitoring"],
  },
];

export function Architecture() {
  return (
    <section id="architecture" className="border-t border-border/50 py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Architecture Overview
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            A clean, layered architecture designed for extensibility and
            maintainability.
          </p>
        </div>

        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
          {layers.map((layer) => (
            <div
              key={layer.title}
              className="rounded-xl border border-border bg-card p-5"
            >
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-primary">
                {layer.title}
              </h3>
              <ul className="space-y-2">
                {layer.items.map((item) => (
                  <li
                    key={item}
                    className="text-sm text-muted-foreground"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
