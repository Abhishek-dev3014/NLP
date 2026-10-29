import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Fingerprint,
  GraduationCap,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
export default function AboutPage() {
  return (
    <div className="page-article">
      <section className="about-hero">
        <div className="feature-icon">
          <ScanLine size={27} />
        </div>
        <p className="eyebrow">THINK CRITICALLY. VERIFY INTELLIGENTLY.</p>
        <h1>
          Better questions.
          <br />A more informed world.
        </h1>
        <p>
          VeriFact AI is a university NLP project exploring fake news detection
          and misinformation analysis. It combines a real machine learning
          pipeline with transparent language observations, helping readers
          approach news with curiosity and care.
        </p>
      </section>
      <div className="concept-grid">
        {[
          {
            icon: GraduationCap,
            title: "Built to learn, built to explain",
            text: "An inspectable TF-IDF, linear SVM, and calibration pipeline makes the journey from words to predictions accessible for students, researchers, and university evaluators.",
          },
          {
            icon: ShieldCheck,
            title: "Scientific honesty, by design",
            text: "A classifier can recognize language associated with training labels. It cannot independently establish whether a factual claim is true or false.",
          },
          {
            icon: Fingerprint,
            title: "Explanations with a clear origin",
            text: "Model contributions, linguistic heuristics, and retrieved fact-checks are labeled separately. Missing evidence and unsupported domains stay visible.",
          },
          {
            icon: BookOpen,
            title: "Your judgment is essential",
            text: "Use the report to guide investigation. Read primary sources, compare independent coverage, and examine the context behind important claims.",
          },
        ].map(({ icon: Icon, title, text }) => (
          <article className="panel concept-card" key={title}>
            <Icon className="text-[var(--accent)] mb-4" size={21} />
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </div>
      <div className="transparency-note">
        <ShieldCheck size={18} />
        <p>
          No account is required. Reports are saved to your anonymous browser
          session on this backend. Article text is stored until you delete it.
          Original uploaded files are not retained. External evidence search is
          optional and requires explicit consent.
        </p>
      </div>
      <div className="flex justify-center mt-8">
        <Button asChild>
          <Link href="/analyze">
            Start with a story <ArrowRight size={15} />
          </Link>
        </Button>
      </div>
    </div>
  );
}
