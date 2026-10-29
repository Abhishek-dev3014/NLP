import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
export function percent(value: number | null | undefined) {
  return value == null ? "Unavailable" : `${(value * 100).toFixed(1)}%`;
}
export function formatDate(value: string) {
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}
export function assessmentClass(label: string) {
  return label === "Likely Credible"
    ? "emerald"
    : label === "Potentially Misleading"
      ? "coral"
      : "amber";
}
