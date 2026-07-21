import Link from "next/link";
import { Shield } from "lucide-react";

const footerLinks = [
  { href: "#features", label: "Features" },
  { href: "#workflow", label: "How It Works" },
  { href: "#architecture", label: "Architecture" },
  { href: "#faq", label: "FAQ" },
];

export function Footer() {
  return (
    <footer className="border-t py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <span className="text-sm font-semibold">SentinelRAG</span>
          </div>

          <nav className="flex items-center gap-6">
            {footerLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {link.label}
              </Link>
            ))}
            <a
              href="https://github.com/chethangowda-web/SentinalRAG"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              GitHub
            </a>
          </nav>

          <p className="text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} SentinelRAG. MIT License.
          </p>
        </div>
      </div>
    </footer>
  );
}
