#!/usr/bin/env node
/**
 * extract-structure.mjs
 *
 * Deterministic structural extraction script for the file-analyzer agent.
 * Uses PluginRegistry (TreeSitterPlugin + non-code parsers) from @understand-anything/core
 * to replace the LLM-generated throwaway regex scripts in Phase 1.
 *
 * Usage:
 *   node extract-structure.mjs <input.json> <output.json>
 *
 * Input JSON:
 *   { projectRoot, batchFiles: [{path, language, sizeLines, fileCategory}], batchImportData }
 *
 * Output JSON:
 *   { scriptCompleted, filesAnalyzed, filesSkipped, results: [...] }
 */

import { createRequire } from 'node:module';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFileSync, writeFileSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
// skills/understand/ -> plugin root is two dirs up
const pluginRoot = resolve(__dirname, '../..');
const require = createRequire(resolve(pluginRoot, 'package.json'));

// ---------------------------------------------------------------------------
// Resolve @understand-anything/core
// ---------------------------------------------------------------------------
let core;
try {
  core = await import(require.resolve('@understand-anything/core'));
} catch {
  // Fallback: direct path for installed plugin cache layouts
  core = await import(resolve(pluginRoot, 'packages/core/dist/index.js'));
}

const { TreeSitterPlugin, PluginRegistry, builtinLanguageConfigs, registerAllParsers } = core;

// ---------------------------------------------------------------------------
// Argument validation
// ---------------------------------------------------------------------------
const [,, inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  process.stderr.write('Usage: node extract-structure.mjs <input.json> <output.json>\n');
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  // Read input
  const inputRaw = readFileSync(inputPath, 'utf-8');
  const input = JSON.parse(inputRaw);
  const { projectRoot, batchFiles, batchImportData } = input;

  if (!projectRoot || !Array.isArray(batchFiles)) {
    throw new Error('Invalid input: must contain projectRoot and batchFiles array');
  }

  // Create tree-sitter plugin with all configs that have WASM grammars
  const tsConfigs = builtinLanguageConfigs.filter(c => c.treeSitter);
  const tsPlugin = new TreeSitterPlugin(tsConfigs);
  await tsPlugin.init();

  // Create registry and register tree-sitter + all non-code parsers
  const registry = new PluginRegistry();
  registry.register(tsPlugin);
  registerAllParsers(registry);

  const results = [];
  const filesSkipped = [];

  for (const file of batchFiles) {
    const absolutePath = join(projectRoot, file.path);

    // Read file content
    let content;
    try {
      content = readFileSync(absolutePath, 'utf-8');
    } catch (err) {
      filesSkipped.push(file.path);
      continue;
    }

    // Line counts
    const lines = content.split('\n');
    const totalLines = lines.length;
    const nonEmptyLines = lines.filter(l => l.trim().length > 0).length;

    // Structural analysis via registry
    let analysis = null;
    try {
      analysis = registry.analyzeFile(file.path, content);
    } catch {
      // If analysis throws, treat as degraded — still include basic metrics
    }

    // Call graph extraction (code files only)
    let callGraph = null;
    if (file.fileCategory === 'code' || file.fileCategory === 'script') {
      try {
        const cg = registry.extractCallGraph(file.path, content);
        if (cg && cg.length > 0) {
          callGraph = cg.map(entry => ({
            caller: entry.caller,
            callee: entry.callee,
            lineNumber: entry.lineNumber,
          }));
        }
      } catch {
        // Call graph extraction failed — non-fatal
      }
    }

    // Build result object
    const result = buildResult(file, totalLines, nonEmptyLines, analysis, callGraph, batchImportData);
    results.push(result);
  }

  // Write output
  const output = {
    scriptCompleted: true,
    filesAnalyzed: results.length,
    filesSkipped,
    results,
  };

  writeFileSync(outputPath, JSON.stringify(output, null, 2), 'utf-8');
}

// ---------------------------------------------------------------------------
// Result builder: maps StructuralAnalysis to the expected output schema
// ---------------------------------------------------------------------------
function buildResult(file, totalLines, nonEmptyLines, analysis, callGraph, batchImportData) {
  const base = {
    path: file.path,
    language: file.language,
    fileCategory: file.fileCategory,
    totalLines,
    nonEmptyLines,
  };

  if (!analysis) {
    // No parser matched — return basic metrics only
    base.metrics = {};
    return base;
  }

  const isCode = file.fileCategory === 'code' || file.fileCategory === 'script' || file.fileCategory === 'markup';

  // Functions (code files)
  if (analysis.functions && analysis.functions.length > 0) {
    base.functions = analysis.functions.map(fn => ({
      name: fn.name,
      startLine: fn.lineRange[0],
      endLine: fn.lineRange[1],
      params: fn.params || [],
    }));
  }

  // Classes (code files)
  if (analysis.classes && analysis.classes.length > 0) {
    base.classes = analysis.classes.map(cls => ({
      name: cls.name,
      startLine: cls.lineRange[0],
      endLine: cls.lineRange[1],
      methods: cls.methods || [],
      properties: cls.properties || [],
    }));
  }

  // Exports (code files)
  if (analysis.exports && analysis.exports.length > 0) {
    base.exports = analysis.exports.map(exp => ({
      name: exp.name,
      line: exp.lineNumber,
      isDefault: false,
    }));
  }

  // Non-code structural data: pass through directly
  if (analysis.sections && analysis.sections.length > 0) {
    base.sections = analysis.sections.map(s => ({
      heading: s.name,
      level: s.level,
      line: s.lineRange[0],
    }));
  }

  if (analysis.definitions && analysis.definitions.length > 0) {
    base.definitions = analysis.definitions.map(d => ({
      name: d.name,
      kind: d.kind,
      fields: d.fields || [],
      startLine: d.lineRange[0],
      endLine: d.lineRange[1],
    }));
  }

  if (analysis.services && analysis.services.length > 0) {
    base.services = analysis.services.map(s => ({
      name: s.name,
      image: s.image,
      ports: s.ports || [],
      ...(s.lineRange ? { startLine: s.lineRange[0], endLine: s.lineRange[1] } : {}),
    }));
  }

  if (analysis.endpoints && analysis.endpoints.length > 0) {
    base.endpoints = analysis.endpoints.map(e => ({
      method: e.method,
      path: e.path,
      startLine: e.lineRange[0],
      endLine: e.lineRange[1],
    }));
  }

  if (analysis.steps && analysis.steps.length > 0) {
    base.steps = analysis.steps.map(s => ({
      name: s.name,
      startLine: s.lineRange[0],
      endLine: s.lineRange[1],
    }));
  }

  if (analysis.resources && analysis.resources.length > 0) {
    base.resources = analysis.resources.map(r => ({
      name: r.name,
      kind: r.kind,
      startLine: r.lineRange[0],
      endLine: r.lineRange[1],
    }));
  }

  // Call graph
  if (callGraph && callGraph.length > 0) {
    base.callGraph = callGraph;
  }

  // Metrics
  const metrics = {};

  // Import count from batchImportData (pre-resolved by project scanner)
  const importPaths = batchImportData?.[file.path];
  if (importPaths) {
    metrics.importCount = importPaths.length;
  } else if (analysis.imports) {
    metrics.importCount = analysis.imports.length;
  }

  if (analysis.exports) {
    metrics.exportCount = analysis.exports.length;
  }
  if (analysis.functions) {
    metrics.functionCount = analysis.functions.length;
  }
  if (analysis.classes) {
    metrics.classCount = analysis.classes.length;
  }
  if (analysis.sections) {
    metrics.sectionCount = analysis.sections.length;
  }
  if (analysis.definitions) {
    metrics.definitionCount = analysis.definitions.length;
  }
  if (analysis.services) {
    metrics.serviceCount = analysis.services.length;
  }
  if (analysis.endpoints) {
    metrics.endpointCount = analysis.endpoints.length;
  }
  if (analysis.steps) {
    metrics.stepCount = analysis.steps.length;
  }
  if (analysis.resources) {
    metrics.resourceCount = analysis.resources.length;
  }

  base.metrics = metrics;

  return base;
}

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------
try {
  await main();
} catch (err) {
  process.stderr.write(`extract-structure.mjs failed: ${err.message}\n${err.stack}\n`);
  process.exit(1);
}
