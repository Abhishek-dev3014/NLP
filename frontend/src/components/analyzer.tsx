"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  BrainCircuit,
  Check,
  CircleHelp,
  FileText,
  Fingerprint,
  Globe,
  Info,
  Link2,
  LoaderCircle,
  LockKeyhole,
  ScanText,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { SAMPLE_HEADLINE, SAMPLE_TEXT, SAMPLE_DISCLOSURE } from "@/lib/sample";
import { Button } from "./ui/button";
import { AnalysisProgress, ErrorState, PageHeading } from "./common";
const formSchema = z.object({
  headline: z.string().max(300, "Use a headline with at most 300 characters."),
  text: z
    .string()
    .max(60000, "Use at most 60,000 characters.")
    .refine(
      (t) => (t.match(/\b[\w]+(?:['’-][\w]+)*\b/g) || []).length >= 12,
      "Enter at least 12 words to analyze the content.",
    ),
});
type FormValues = z.infer<typeof formSchema>;
type Mode = "text" | "url" | "file";
export function Analyzer() {
  const router = useRouter();
  const client = useQueryClient();
  const [mode, setMode] = useState<Mode>("text");
  const [url, setUrl] = useState("");
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);
  const [review, setReview] = useState(false);
  const [consent, setConsent] = useState(false);
  const [extractionError, setExtractionError] = useState("");
  const {
    register,
    handleSubmit,
    control,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { headline: "", text: "" },
  });
  useEffect(() => {
    const claim = sessionStorage.getItem("verifact-claim");
    if (claim) {
      reset({ headline: "Claim selected for review", text: claim });
      sessionStorage.removeItem("verifact-claim");
    }
  }, [reset]);
  const text = useWatch({ control, name: "text" });
  const words = (text.match(/\b[\w]+(?:['’-][\w]+)*\b/g) || []).length;
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      api.analyze({
        ...values,
        input_type: mode,
        source_url: sourceUrl,
        allow_external_evidence: consent,
      }),
    onSuccess: async (result) => {
      client.setQueryData(["analysis", result.id], result);
      await client.invalidateQueries({ queryKey: ["analyses"] });
      await client.invalidateQueries({ queryKey: ["stats"] });
      router.push(`/results/${result.id}`);
    },
  });
  const extraction = useMutation({
    mutationFn: async (input: { url: string } | { file: File }) =>
      "url" in input ? api.extractUrl(input.url) : api.extractFile(input.file),
    onSuccess: (result) => {
      setValue("headline", result.headline);
      setValue("text", result.text, { shouldValidate: true });
      setSourceUrl(result.source_url);
      setDemo(false);
      setReview(true);
      setExtractionError("");
    },
    onError: (error) => setExtractionError(error.message),
  });
  const busy = mutation.isPending || extraction.isPending;
  function changeMode(next: Mode) {
    if (busy) return;
    setMode(next);
    reset();
    setDemo(false);
    setReview(false);
    setSourceUrl(null);
    setExtractionError("");
    mutation.reset();
    extraction.reset();
  }
  function loadSample() {
    reset({ headline: SAMPLE_HEADLINE, text: SAMPLE_TEXT });
    setDemo(true);
    setReview(true);
    setSourceUrl(null);
  }
  function upload(file: File | undefined) {
    if (!file) return;
    if (!/\.(pdf|txt)$/i.test(file.name)) {
      setExtractionError("Choose a .txt or .pdf document.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setExtractionError("The file must be 5 MB or smaller.");
      return;
    }
    setExtractionError("");
    extraction.mutate({ file });
  }
  const showEditor = mode === "text" || review;
  return (
    <>
      <PageHeading
        eyebrow="THE NEWS, THROUGH A DIFFERENT LENS"
        title="Analyze news with AI"
        description="Get a fake-news screening result, understand why the model predicted it, and identify claims to verify."
        action={
          <Button variant="outline" size="sm" asChild>
            <Link href="/history">
              <FileText size={13} /> View history
            </Link>
          </Button>
        }
      />
      {mutation.isPending && <AnalysisProgress />}
      {mutation.isError && <ErrorState message={mutation.error.message} />}
      <div className="report-guide">
        <div>
          <span>01</span>
          <strong>Add your content</strong>
          <p>Paste English text, enter a public URL, or upload a document.</p>
        </div>
        <div>
          <span>02</span>
          <strong>Get your assessment</strong>
          <p>
            Get a credibility prediction, its confidence, and the main reasons.
          </p>
        </div>
        <div>
          <span>03</span>
          <strong>Review the evidence</strong>
          <p>Inspect short claims and follow up with primary sources.</p>
        </div>
      </div>
      <div className="analyzer-grid">
        <section className="panel">
          <div
            className="input-tabs"
            role="tablist"
            aria-label="Article input mode"
          >
            {[
              { id: "text", label: "Paste text", icon: ScanText },
              { id: "url", label: "Analyze URL", icon: Link2 },
              { id: "file", label: "Upload document", icon: Upload },
            ].map(({ id, label, icon: Icon }, index) => (
              <button
                key={id}
                id={`tab-${id}`}
                aria-selected={mode === id}
                aria-controls="input-panel"
                tabIndex={mode === id ? 0 : -1}
                role="tab"
                className="input-tab"
                disabled={busy}
                onClick={() => changeMode(id as Mode)}
                onKeyDown={(e) => {
                  if (
                    ["ArrowRight", "ArrowLeft", "Home", "End"].includes(e.key)
                  ) {
                    e.preventDefault();
                    const ids: Mode[] = ["text", "url", "file"];
                    const next =
                      e.key === "Home"
                        ? 0
                        : e.key === "End"
                          ? 2
                          : (index + (e.key === "ArrowRight" ? 1 : 2)) % 3;
                    changeMode(ids[next]);
                    document.getElementById(`tab-${ids[next]}`)?.focus();
                  }
                }}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>
          <form
            onSubmit={handleSubmit((values) => mutation.mutate(values))}
            className="form-workspace"
            id="input-panel"
            role="tabpanel"
            aria-labelledby={`tab-${mode}`}
          >
            {mode === "url" && (
              <div>
                <label className="input-label" htmlFor="article-url">
                  Public article URL
                </label>
                <div className="flex gap-2">
                  <input
                    className="text-input"
                    id="article-url"
                    type="url"
                    placeholder="https://example.com/news/article"
                    value={url}
                    disabled={busy}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy || !url.trim()}
                    onClick={() => {
                      try {
                        const target = new URL(url);
                        if (!["http:", "https:"].includes(target.protocol))
                          throw Error();
                        extraction.mutate({ url });
                      } catch {
                        setExtractionError(
                          "Enter a complete public HTTP or HTTPS URL.",
                        );
                      }
                    }}
                  >
                    {extraction.isPending ? (
                      <LoaderCircle className="spin" size={14} />
                    ) : (
                      <Globe size={14} />
                    )}{" "}
                    Extract
                  </Button>
                </div>
                <p className="input-note">
                  Paste a full article link, including MSN links. Extract the
                  text, review it, then choose Analyze article. Publishers
                  requiring sign-in may need a manual paste.
                </p>
              </div>
            )}
            {mode === "file" && (
              <>
                <label
                  className="upload-zone"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (!busy) upload(e.dataTransfer.files[0]);
                  }}
                >
                  <Upload size={26} />
                  <strong>
                    {extraction.isPending
                      ? "Extracting document text…"
                      : "Choose a document or drag it here"}
                  </strong>
                  <p>TXT or text-based PDF · Up to 5 MB · 50 pages</p>
                  <input
                    aria-label="Upload article document"
                    type="file"
                    accept=".txt,.pdf,text/plain,application/pdf"
                    disabled={busy}
                    onChange={(e) => {
                      upload(e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                </label>
                <p className="input-note">
                  <LockKeyhole size={11} className="inline mr-1" /> Documents
                  are processed by your backend. Original files are not stored
                  or sent to third-party APIs.
                </p>
              </>
            )}
            {extractionError && (
              <div>
                <ErrorState message={extractionError} />
                <Button
                  type="button"
                  variant="outline"
                  className="mt-3"
                  onClick={() => changeMode("text")}
                >
                  Paste article text instead <ArrowRight size={13} />
                </Button>
              </div>
            )}
            {showEditor && (
              <div className={mode !== "text" ? "extracted-preview" : ""}>
                {review && mode !== "text" && (
                  <p className="success-message mb-4">
                    <Check size={13} /> Content extracted. Review and edit it
                    before analysis.
                  </p>
                )}
                <div className="field-group">
                  <label htmlFor="headline" className="input-label">
                    Article headline <span>(optional)</span>
                  </label>
                  <input
                    id="headline"
                    className="text-input"
                    placeholder="Give this story a little context…"
                    maxLength={300}
                    disabled={busy}
                    {...register("headline")}
                  />
                  {errors.headline && (
                    <p className="validation-error">
                      {errors.headline.message}
                    </p>
                  )}
                </div>
                <div className="field-group">
                  <div className="input-row">
                    <label htmlFor="article-text" className="input-label">
                      Article content
                    </label>
                    <div className="flex gap-3">
                      {mode === "text" && (
                        <button
                          type="button"
                          className="text-action"
                          disabled={busy}
                          onClick={loadSample}
                        >
                          <Sparkles size={11} /> Try an example
                        </button>
                      )}
                      {text && (
                        <button
                          className="text-action"
                          type="button"
                          disabled={busy}
                          onClick={() => {
                            reset();
                            setDemo(false);
                          }}
                        >
                          <X size={11} /> Clear
                        </button>
                      )}
                    </div>
                  </div>
                  {demo && (
                    <div className="demo-note">
                      <Info size={12} />
                      {SAMPLE_DISCLOSURE}
                    </div>
                  )}
                  <textarea
                    id="article-text"
                    aria-invalid={!!errors.text}
                    aria-describedby={
                      errors.text ? "content-error" : "content-help"
                    }
                    className="textarea"
                    placeholder={
                      "Paste the article or claim you’d like to explore.\n\nInclude enough context for a meaningful analysis. The model will examine language patterns, identify relevant features, and surface claims worth verifying."
                    }
                    maxLength={60000}
                    disabled={busy}
                    {...register("text")}
                  />
                  {errors.text && (
                    <p
                      id="content-error"
                      className="validation-error"
                      role="alert"
                    >
                      {errors.text.message}
                    </p>
                  )}
                  <div className="word-counter" id="content-help">
                    <span>Minimum 12 words · English content</span>
                    <div className="counter-group">
                      <span>{words.toLocaleString()} words</span>
                      <span>
                        {text.length.toLocaleString()} / 60,000 characters
                      </span>
                    </div>
                  </div>
                </div>
                {words >= 12 && (
                  <div className="scope-note" role="status">
                    <strong>
                      {words >= 40 ? "Article screening" : "Short excerpt"}
                    </strong>
                    <p>
                      {words >= 40
                        ? "You’ll receive a trained article classification, model confidence, explanations, and claims to verify. The prediction is not an independent fact-check."
                        : "A full article gives the model more context. Short excerpts receive a preliminary estimate and may be marked uncertain."}
                    </p>
                  </div>
                )}
                {health.data?.evidence_configured && (
                  <label className="consent-label">
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(e) => setConsent(e.target.checked)}
                      disabled={busy}
                    />
                    <span>
                      Search external fact-checks. This sends the headline or
                      first candidate claim to Google Fact Check Tools. The full
                      article stays with this backend.
                    </span>
                  </label>
                )}
                <div className="form-bottom">
                  <p>
                    <LockKeyhole size={11} /> Saved privately to this browser
                    session. You can delete your analysis at any time.
                  </p>
                  <Button type="submit" disabled={busy}>
                    {mutation.isPending ? (
                      <LoaderCircle size={15} className="spin" />
                    ) : (
                      <Sparkles size={15} />
                    )}{" "}
                    {mutation.isPending
                      ? "Analyzing article…"
                      : "Analyze article"}{" "}
                    {!mutation.isPending && <ArrowRight size={14} />}
                  </Button>
                </div>
              </div>
            )}
          </form>
          <div className="form-footnote">
            <ShieldCheck size={11} /> AI identifies language patterns. It does
            not independently verify factual accuracy.
          </div>
        </section>
        <aside className="analyzer-aside">
          <div className="panel side-info">
            <h3>
              <BrainCircuit size={16} /> A closer look at your content
            </h3>
            <ul className="analysis-checklist">
              {[
                {
                  icon: ScanText,
                  title: "Language patterns",
                  text: "A clear summary, named entities, and wording cues.",
                },
                {
                  icon: Fingerprint,
                  title: "Explainable predictions",
                  text: "Inspect word contributions and confidence limitations.",
                },
                {
                  icon: FileText,
                  title: "Claims worth verifying",
                  text: "Candidate statements to investigate.",
                },
                {
                  icon: ShieldCheck,
                  title: "Transparent limitations",
                  text: "Clear confidence and domain disclosures.",
                },
              ].map(({ icon: Icon, title, text }) => (
                <li key={title}>
                  <Icon size={14} />
                  <div>
                    <strong>{title}</strong>
                    <p>{text}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="panel side-info tip-card">
            <h3>
              <CircleHelp size={16} /> A prediction isn’t a verdict
            </h3>
            <p>
              The article model learns from historical English news. Its
              benchmark score does not guarantee accuracy on current Indian
              news. Always check the original evidence.
            </p>
            <Link href="/how-it-works">
              Understand the methodology <ArrowUpRight size={12} />
            </Link>
          </div>
          <div className="panel side-info">
            <h3>
              <BookOpen size={15} /> Made for curious minds
            </h3>
            <p>
              Use this workspace to ask better questions, compare language, and
              practice critical reading.
            </p>
            <Link className="section-link mt-4" href="/model-performance">
              Explore model performance <ArrowUpRight size={12} />
            </Link>
          </div>
        </aside>
      </div>
    </>
  );
}
