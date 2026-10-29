"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, FlaskConical, LoaderCircle } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeading, ErrorState } from "./common";
import { NLPInspector } from "./nlp-inspector";
import { Button } from "./ui/button";
const example =
  "Maya visited the city library in London on Monday. She borrowed three books about renewable energy. The library runs a weekly reading group for students interested in science and technology.";
export function NLPLab() {
  const [text, setText] = useState(example);
  const mutation = useMutation({ mutationFn: api.explore });
  return (
    <>
      <PageHeading
        eyebrow="LEARN BY EXPLORING"
        title="Your NLP lab"
        description="See how a sentence becomes structured information. Change the text and inspect the result."
      />
      <div className="lab-concepts">
        <span>Unit 1 · Tokens, lemmas, POS & NER</span>
        <span>Unit 2 · Dependency parsing</span>
        <span>Unit 5 · Extractive summarization</span>
      </div>
      <form
        className="panel panel-body mb-6"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate(text);
        }}
      >
        <label htmlFor="lab-text" className="input-label">
          English text to explore
        </label>
        <textarea
          id="lab-text"
          className="textarea lab-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={60000}
          disabled={mutation.isPending}
        />
        <div className="form-bottom">
          <p>
            At least 12 words. Processed locally; lab results are not saved to
            history. The starter example is fictional.
          </p>
          <Button
            type="submit"
            disabled={
              mutation.isPending ||
              (text.match(/\b[\w]+(?:['’-][\w]+)*\b/g) || []).length < 12
            }
          >
            {mutation.isPending ? (
              <LoaderCircle size={16} className="spin" />
            ) : (
              <FlaskConical size={16} />
            )}{" "}
            Explore language <ArrowRight size={15} />
          </Button>
        </div>
      </form>
      {mutation.isError && <ErrorState message={mutation.error.message} />}
      {mutation.data && <NLPInspector data={mutation.data} />}
      <div className="info-note">
        This lab explains linguistic structure. It does not classify
        credibility. Transformer-feature experiments and model evaluation are
        documented under Model information.
      </div>
    </>
  );
}
