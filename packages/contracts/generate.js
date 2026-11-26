/**
 * Zero-dependency OpenAPI 3.1 -> TypeScript Contract Generator (`@dbazar/contracts`).
 * Reads `packages/contracts/openapi.json` (exported from Django `manage.py export_openapi`)
 * and generates strict TypeScript interfaces in `src/schema.d.ts`.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const openapiJsonPath = path.join(__dirname, "openapi.json");
const outDir = path.join(__dirname, "src");
const outFile = path.join(outDir, "schema.d.ts");

function toTsType(prop) {
  if (!prop) return "unknown";
  if (prop.$ref) {
    const parts = prop.$ref.split("/");
    return parts[parts.length - 1] || "unknown";
  }
  if (prop.enum && prop.enum.length > 0) {
    return prop.enum.map((v) => JSON.stringify(v)).join(" | ");
  }
  if (prop.anyOf) {
    return prop.anyOf
      .map((sub) => (sub.type === "null" ? "null" : toTsType(sub)))
      .join(" | ");
  }
  if (prop.type === "string") return "string";
  if (prop.type === "integer" || prop.type === "number") return "number";
  if (prop.type === "boolean") return "boolean";
  if (prop.type === "array") return `${toTsType(prop.items)}[]`;
  if (prop.type === "object" && prop.properties) {
    const req = new Set(prop.required || []);
    const fields = Object.entries(prop.properties).map(
      ([k, v]) => `${k}${req.has(k) ? "" : "?"}: ${toTsType(v)};`
    );
    return `{ ${fields.join(" ")} }`;
  }
  return "Record<string, unknown>";
}

export function generateContracts() {
  const raw = fs.readFileSync(openapiJsonPath, "utf-8");
  const spec = JSON.parse(raw);
  const schemas = spec.components?.schemas || {};
  const paths = spec.paths || {};

  const lines = [
    "// AUTO-GENERATED FROM packages/contracts/openapi.yaml (Django 5 -> TypeScript Contract-First)",
    "// Do not edit manually. Run `node packages/contracts/generate.js`.",
    "",
  ];

  for (const [name, schema] of Object.entries(schemas)) {
    const req = new Set(schema.required || []);
    lines.push(`export interface ${name} {`);
    for (const [propName, propSchema] of Object.entries(schema.properties || {})) {
      const opt = req.has(propName) ? "" : "?";
      lines.push(`  ${propName}${opt}: ${toTsType(propSchema)};`);
    }
    lines.push("}", "");
  }

  lines.push("export interface ApiOperations {");
  for (const [routePath, methods] of Object.entries(paths)) {
    for (const [method, op] of Object.entries(methods)) {
      const opId = op.operationId || `${method}_${routePath}`;
      const reqRef = op.requestBody?.content?.["application/json"]?.schema;
      const resp200 =
        op.responses?.["200"]?.content?.["application/json"]?.schema ||
        op.responses?.["201"]?.content?.["application/json"]?.schema;
      lines.push(`  ${opId}: {`);
      lines.push(`    method: ${JSON.stringify(method.toUpperCase())};`);
      lines.push(`    path: ${JSON.stringify(routePath)};`);
      lines.push(`    request: ${reqRef ? toTsType(reqRef) : "void"};`);
      lines.push(`    response: ${resp200 ? toTsType(resp200) : "unknown"};`);
      lines.push("  };");
    }
  }
  lines.push("}", "");

  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(outFile, lines.join("\n"), "utf-8");
  return {
    schemaCount: Object.keys(schemas).length,
    pathCount: Object.keys(paths).length,
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const res = generateContracts();
  console.log(`Generated ${res.schemaCount} TypeScript schemas and ${res.pathCount} API paths into ${outFile}`);
}
