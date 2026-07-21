import { Navbar } from "@/components/navbar";
import { Hero } from "@/components/hero";
import { Features } from "@/components/features";
import { Architecture } from "@/components/architecture";
import { Stats } from "@/components/stats";
import { Workflow } from "@/components/workflow";
import { Faq } from "@/components/faq";
import { Footer } from "@/components/footer";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <Stats />
        <Workflow />
        <Architecture />
        <Faq />
      </main>
      <Footer />
    </div>
  );
}
