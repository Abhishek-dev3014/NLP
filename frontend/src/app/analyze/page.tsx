import type { Metadata } from "next";
import { Analyzer } from "@/components/analyzer";
export const metadata: Metadata = { title: "Analyze news" };
export default function AnalyzePage() {
  return <Analyzer />;
}
