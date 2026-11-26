/**
 * `@dbazar/ui-tokens` — Design tokens, zero-jargon Uzbek dictionary, and UX compliance guards.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const designTokens = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "tokens.json"), "utf-8")
);

export const uzDictionary = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "i18n", "uz.json"), "utf-8")
);

export const FORBIDDEN_UI_JARGON = ["SKU", "VMI", "Sell-Through", "Escrow", "Sub-order"];

export function assertZeroJargonInText(visibleText) {
  for (const term of FORBIDDEN_UI_JARGON) {
    const regex = new RegExp(`\\b${term}\\b`, "i");
    if (regex.test(visibleText)) {
      throw new Error(
        `UI Jargon qoidabuzarligi: Foydalanuvchi ekranida '${term}' so'zi ishlatilishi taqiqlanadi (/ui-minimalist-design).`
      );
    }
  }
}

export function resolveThemeAttribute(mode, systemPrefersDark = false) {
  if (mode === "system") {
    return systemPrefersDark ? "dark" : "light";
  }
  return mode;
}
