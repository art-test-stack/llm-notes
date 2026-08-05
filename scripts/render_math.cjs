#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const katex = require("katex");

const MATH_ELEMENT = /<(span|div)\b([^>]*\bclass=(['"])[^'"]*\bmath-(inline|display)\b[^'"]*\3[^>]*)>([\s\S]*?)<\/\1>/gi;
const CODE_ELEMENT = /<code\b(?![^>]*\blanguage-)([^>]*)>([\s\S]*?)<\/code>/gi;
const DATA_TEX = /\bdata-tex=(['"])([\s\S]*?)\1/i;
const TAGS = /<[^>]+>/g;
const NAMED_ENTITIES = {
  alpha: "α", beta: "β", gamma: "γ", delta: "δ", epsilon: "ε", theta: "θ",
  lambda: "λ", mu: "μ", pi: "π", sigma: "σ", phi: "φ", omega: "ω",
  Alpha: "Α", Beta: "Β", Gamma: "Γ", Delta: "Δ", Theta: "Θ", Lambda: "Λ",
  Pi: "Π", Sigma: "Σ", Phi: "Φ", Omega: "Ω", sup2: "²", sup3: "³",
  times: "×", middot: "·", isin: "∈", notin: "∉", le: "≤", ge: "≥", ne: "≠",
  asymp: "≈", sum: "∑", prod: "∏", infin: "∞", part: "∂", nabla: "∇",
};

function decodeHtml(value) {
  return value
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&#([0-9]+);/g, (_, code) => String.fromCodePoint(parseInt(code, 10)))
    .replace(/&([A-Za-z][A-Za-z0-9]+);/g, (whole, name) => NAMED_ENTITIES[name] ?? whole)
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function escapeAttribute(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function promoteReviewedCode(source, topicId, entries) {
  const byText = new Map();
  for (const entry of entries) {
    if (!entry || typeof entry.text !== "string" || typeof entry.tex !== "string" || !Number.isInteger(entry.occurrences) || entry.occurrences < 1) {
      throw new Error(`${topicId}: invalid math-code promotion entry`);
    }
    if (byText.has(entry.text)) {
      throw new Error(`${topicId}: duplicate math-code promotion for ${JSON.stringify(entry.text)}`);
    }
    byText.set(entry.text, {...entry, seen: 0});
  }

  const promoted = source.replace(CODE_ELEMENT, (whole, attrs, body) => {
    const visible = decodeHtml(body.replace(TAGS, " ")).replace(/\s+/g, " ").trim();
    const entry = byText.get(visible);
    if (!entry) return whole;
    entry.seen += 1;
    return `<span class="math-inline" data-tex="${escapeAttribute(entry.tex)}">${body}</span>`;
  });

  let total = 0;
  for (const entry of byText.values()) {
    if (entry.seen !== entry.occurrences) {
      throw new Error(
        `${topicId}: promoted ${entry.seen} occurrences of ${JSON.stringify(entry.text)}, expected ${entry.occurrences}`,
      );
    }
    total += entry.seen;
  }
  return {source: promoted, promoted: total};
}

function renderFragment(source, topicId, expectedCount, promotionEntries) {
  const promotion = promoteReviewedCode(source, topicId, promotionEntries);
  let rendered = 0;
  const output = promotion.source.replace(
    MATH_ELEMENT,
    (whole, tag, attrs, quote, kind) => {
      const texMatch = attrs.match(DATA_TEX);
      if (!texMatch) {
        throw new Error(`${topicId}: math element is missing data-tex`);
      }
      const tex = decodeHtml(texMatch[2]).trim();
      if (!tex) {
        throw new Error(`${topicId}: math element has empty data-tex`);
      }
      let staticMarkup;
      try {
        staticMarkup = katex.renderToString(tex, {
          displayMode: kind.toLowerCase() === "display",
          output: "htmlAndMathml",
          throwOnError: true,
          strict: "warn",
          trust: false,
          maxExpand: 1000,
          maxSize: 20,
        });
      } catch (error) {
        throw new Error(`${topicId}: KaTeX could not render ${JSON.stringify(tex)}: ${error.message}`);
      }
      rendered += 1;
      const wrapper = kind.toLowerCase() === "display" ? "div" : "span";
      return `<${wrapper} class="math-${kind.toLowerCase()}" data-rendered="katex-static">${staticMarkup}</${wrapper}>`;
    },
  );

  const expectedRendered = expectedCount + promotion.promoted;
  if (rendered !== expectedRendered) {
    throw new Error(`${topicId}: rendered ${rendered} equations, expected ${expectedRendered}`);
  }
  if (/\bdata-tex=/.test(output)) {
    throw new Error(`${topicId}: unrendered data-tex remains in generated output`);
  }
  return {output, rendered, promoted: promotion.promoted};
}

function main() {
  const [sourceDirArg, outputDirArg, manifestArg, promotionsArg] = process.argv.slice(2);
  if (!sourceDirArg || !outputDirArg || !manifestArg) {
    throw new Error("Usage: render_math.cjs SOURCE_DIR OUTPUT_DIR MANIFEST_JSON [PROMOTIONS_JSON]");
  }

  const sourceDir = path.resolve(sourceDirArg);
  const outputDir = path.resolve(outputDirArg);
  const manifestPath = path.resolve(manifestArg);
  const promotionsPath = promotionsArg
    ? path.resolve(promotionsArg)
    : path.join(path.dirname(manifestPath), "math-code-promotions.json");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const promotions = JSON.parse(fs.readFileSync(promotionsPath, "utf8"));
  if (manifest.schema_version !== 2 || !Array.isArray(manifest.chapters)) {
    throw new Error("Expected chapter manifest schema version 2");
  }
  if (promotions.schema_version !== 1 || typeof promotions.chapters !== "object" || !Number.isInteger(promotions.total_occurrences)) {
    throw new Error("Expected math-code promotion schema version 1");
  }

  fs.rmSync(outputDir, {recursive: true, force: true});
  fs.mkdirSync(outputDir, {recursive: true});
  let totalRendered = 0;
  let totalPromoted = 0;
  const knownTopics = new Set(manifest.chapters.map((entry) => entry.id));
  for (const topicId of Object.keys(promotions.chapters)) {
    if (!knownTopics.has(topicId)) {
      throw new Error(`Unknown topic in math-code promotions: ${topicId}`);
    }
  }

  for (const entry of manifest.chapters) {
    const sourcePath = path.join(sourceDir, `${entry.id}.html`);
    const outputPath = path.join(outputDir, `${entry.id}.html`);
    const source = fs.readFileSync(sourcePath, "utf8");
    const result = renderFragment(source, entry.id, entry.math_expressions, promotions.chapters[entry.id] || []);
    fs.writeFileSync(outputPath, result.output, "utf8");
    totalRendered += result.rendered;
    totalPromoted += result.promoted;
  }

  if (totalPromoted !== promotions.total_occurrences) {
    throw new Error(`Promoted ${totalPromoted} code expressions, promotion registry declares ${promotions.total_occurrences}`);
  }
  const expectedTotal = manifest.total_math_expressions + promotions.total_occurrences;
  if (totalRendered !== expectedTotal) {
    throw new Error(`Rendered ${totalRendered} equations, expected ${expectedTotal}`);
  }
  process.stdout.write(
    `Rendered ${totalRendered} static KaTeX expressions (${manifest.total_math_expressions} canonical TeX + ${totalPromoted} reviewed code promotions).\n`,
  );
}

try {
  main();
} catch (error) {
  console.error(error.stack || error.message);
  process.exit(1);
}
