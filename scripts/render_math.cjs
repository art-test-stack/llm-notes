#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const katex = require("katex");

const MATH_ELEMENT = /<(span|div)\b([^>]*\bclass=(['"])[^'"]*\bmath-(inline|display)\b[^'"]*\3[^>]*)>([\s\S]*?)<\/\1>/gi;
const DATA_TEX = /\bdata-tex=(['"])([\s\S]*?)\1/i;

function decodeHtml(value) {
  return value
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&#([0-9]+);/g, (_, code) => String.fromCodePoint(parseInt(code, 10)))
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function renderFragment(source, topicId, expectedCount) {
  let rendered = 0;
  const output = source.replace(
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
      let mathml;
      try {
        mathml = katex.renderToString(tex, {
          displayMode: kind.toLowerCase() === "display",
          output: "mathml",
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
      return `<${wrapper} class="math-${kind.toLowerCase()}" data-rendered="katex-mathml">${mathml}</${wrapper}>`;
    },
  );

  if (rendered !== expectedCount) {
    throw new Error(`${topicId}: rendered ${rendered} equations, expected ${expectedCount}`);
  }
  if (/\bdata-tex=/.test(output)) {
    throw new Error(`${topicId}: unrendered data-tex remains in generated output`);
  }
  return output;
}

function main() {
  const [sourceDirArg, outputDirArg, manifestArg] = process.argv.slice(2);
  if (!sourceDirArg || !outputDirArg || !manifestArg) {
    throw new Error("Usage: render_math.cjs SOURCE_DIR OUTPUT_DIR MANIFEST_JSON");
  }

  const sourceDir = path.resolve(sourceDirArg);
  const outputDir = path.resolve(outputDirArg);
  const manifest = JSON.parse(fs.readFileSync(path.resolve(manifestArg), "utf8"));
  if (manifest.schema_version !== 2 || !Array.isArray(manifest.chapters)) {
    throw new Error("Expected chapter manifest schema version 2");
  }

  fs.rmSync(outputDir, { recursive: true, force: true });
  fs.mkdirSync(outputDir, { recursive: true });
  let total = 0;

  for (const entry of manifest.chapters) {
    const sourcePath = path.join(sourceDir, `${entry.id}.html`);
    const outputPath = path.join(outputDir, `${entry.id}.html`);
    const source = fs.readFileSync(sourcePath, "utf8");
    const rendered = renderFragment(source, entry.id, entry.math_expressions);
    fs.writeFileSync(outputPath, rendered, "utf8");
    total += entry.math_expressions;
  }

  if (total !== manifest.total_math_expressions) {
    throw new Error(`Rendered ${total} equations, manifest declares ${manifest.total_math_expressions}`);
  }
  process.stdout.write(`Rendered ${total} TeX expressions to static KaTeX MathML.\n`);
}

try {
  main();
} catch (error) {
  console.error(error.stack || error.message);
  process.exit(1);
}
