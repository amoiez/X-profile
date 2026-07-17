import { z } from "zod";

// Shared analyze-form schema (also unit-tested).
export const analyzeSchema = z.object({
  username: z
    .string()
    .trim()
    .min(1, "Enter a username.")
    .transform((v) => v.replace(/^@/, ""))
    .refine((v) => /^[A-Za-z0-9_]{1,15}$/.test(v), {
      message: "1–15 characters: letters, digits, or underscores only.",
    }),
  post_limit: z.coerce.number().int().min(10).max(500),
});

export type AnalyzeInput = z.input<typeof analyzeSchema>;
