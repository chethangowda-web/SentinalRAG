import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** The cross-encoder reranker returns a raw logit (e.g. 3.159 or -3.244); show it as a 0-100% relevance. */
export function rerankPercent(score: number): number {
  return Math.round(100 / (1 + Math.exp(-score)));
}
