import { createHash } from "node:crypto";
import { closeSync, constants, fstatSync, openSync, readFileSync, readSync, statSync } from "node:fs";
import { join } from "node:path";

const profile = JSON.parse(readFileSync(new URL("../handoff-profile.json", import.meta.url), "utf8"));
export const GRAPH_BYTES = profile.files["graph.json"];
export const RECEIPT_BYTES = profile.files["receipt.json"];
export const PINNED_PRODUCER = profile.producer_version;
const bundleHeader = "graphify-handoff-v2\n";

export function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function rejectDuplicateKeys(text, filename) {
  const objects = [];
  let lastString;
  // Native JSON.parse has already validated the syntax. A colon can only
  // follow an object member name, and quoted tokens are consumed whole.
  for (const [token] of text.matchAll(/"(?:[^"\\]|\\.)*"|[{}:\[\]]/g)) {
    switch (token) {
      case "{": objects.push(new Set()); break;
      case "[": objects.push(null); break;
      case "}":
      case "]": objects.pop(); break;
      case ":": {
        const key = JSON.parse(lastString);
        const keys = objects.at(-1);
        if (keys.has(key)) throw new Error("Duplicate JSON key in " + filename);
        keys.add(key);
        break;
      }
      default: lastString = token;
    }
  }
}

export function readBytes(path, maxBytes, remaining = Infinity) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) throw new Error("Invalid artifact byte budget");
  if (!statSync(path).isFile()) throw new Error("Artifact is not a regular file");
  const fd = openSync(path, constants.O_RDONLY | (constants.O_NONBLOCK ?? 0));
  try {
    const stat = fstatSync(fd);
    if (!stat.isFile() || stat.size > maxBytes) throw new Error("Artifact exceeds byte budget or is not a regular file");
    if (stat.size + String(stat.size).length + 1 > remaining) throw new Error("Remaining handoff byte budget exceeded");
    const buffer = Buffer.alloc(stat.size);
    let size = 0;
    while (size < buffer.length) {
      const read = readSync(fd, buffer, size, buffer.length - size, null);
      if (!read) break;
      size += read;
    }
    if (size !== stat.size || readSync(fd, Buffer.alloc(1), 0, 1, null)) {
      throw new Error("Artifact changed size during bounded read");
    }
    return buffer.subarray(0, size);
  } finally {
    closeSync(fd);
  }
}

function readJSON(read, filename, maxBytes) {
  let raw;
  try {
    raw = read(filename, maxBytes);
  } catch (err) {
    throw new Error("Cannot read " + filename + ": " + (err.code ?? err.message));
  }
  return [raw, parseEvidenceObject(raw, filename)];
}

export function parseEvidenceObject(raw, filename) {
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(raw);
  } catch {
    throw new Error("Invalid UTF-8 in " + filename);
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Error("Invalid JSON in " + filename);
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Expected an object in " + filename);
  }
  rejectDuplicateKeys(text, filename);
  return value;
}

const relations = new Set(["documented_in", "changed_in", "tested_by", "implemented_in"]);

const structuralRelations = new Set(["contains_feature", "contains_source", "located_in"]);
const digestPattern = /^[a-f0-9]{64}$/;

function ordinaryRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function repositoryPath(path) {
  return typeof path === "string" && path.trim().length > 0 && !/[\\:\p{C}]/u.test(path) &&
    path.split("/").every((part) => part !== "" && part !== "." && part !== ".." && part !== ".git");
}

export function inspectEvidence(directory, sourceCommit, options) {
  return inspect((name, limit) => readBytes(join(directory, name), limit), sourceCommit, options);
}

export function inspectEvidenceBytes(graph, receipt, sourceCommit, options) {
  return inspect((name, limit) => {
    const bytes = name === "graph.json" ? graph : receipt;
    if (bytes.length > limit) throw new Error("Artifact exceeds byte budget");
    return bytes;
  }, sourceCommit, options);
}

function inspect(read, sourceCommit, {
  repository, templateVersion, producerVersion, sourceBlobs,
  maxGraphBytes = profile.files["graph.json"], maxReceiptBytes = profile.files["receipt.json"],
} = {}) {
  const [bytes, graph] = readJSON(read, "graph.json", maxGraphBytes);
  const [, receipt] = readJSON(read, "receipt.json", maxReceiptBytes);
  if (receipt.schema_version !== 1) throw new Error("Unsupported receipt schema");
  if (!Array.isArray(graph.nodes) || !Array.isArray(graph.links)) throw new Error("Invalid graph shape");
  if (!/^[a-f0-9]{40}$/.test(sourceCommit) || graph.built_at_commit !== sourceCommit ||
      receipt.source_commit !== sourceCommit) throw new Error("Source commit mismatch");
  const digest = sha256(bytes);
  if (receipt.graph_sha256 !== digest) throw new Error("Graph digest mismatch");
  if (receipt.nodes !== graph.nodes.length) throw new Error("Node count mismatch");
  if (receipt.edges !== graph.links.length) throw new Error("Edge count mismatch");
  if (receipt.mcp_verified !== true) throw new Error("Receipt lacks MCP verification");

  if (graph.directed !== true || graph.multigraph !== false) throw new Error("Expected a directed simple graph");
  if (!ordinaryRecord(graph.graph) || graph.graph.scope !== "feature-evidence" ||
      receipt.scope !== graph.graph.scope || (repository !== undefined && receipt.repository !== repository)) {
    throw new Error("Evidence scope or repository mismatch");
  }
  if (typeof receipt.template_version !== "string" || receipt.template_version !== graph.graph.template_version ||
      (templateVersion !== undefined && receipt.template_version !== templateVersion)) {
    throw new Error("Evidence template version mismatch");
  }
  if (producerVersion !== undefined &&
      (receipt.graphify_version !== producerVersion ||
       (graph.graph.graphify_version !== undefined && graph.graph.graphify_version !== producerVersion))) {
    throw new Error("Graphify producer version mismatch");
  }
  if (!Array.isArray(receipt.source_files) || !ordinaryRecord(receipt.source_sha256)) {
    throw new Error("Invalid source inventory");
  }
  const inventory = new Set(receipt.source_files);
  if (inventory.size !== receipt.source_files.length || [...inventory].some((path) => !repositoryPath(path))) {
    throw new Error("Invalid source inventory");
  }
  const nodes = new Map();
  const summaries = new Map();
  for (const node of graph.nodes) {
    if (typeof node?.id !== "string" || !node.id) throw new Error("Invalid node ID");
    if (nodes.has(node.id)) throw new Error("Duplicate node ID: " + node.id);
    if (typeof node.label !== "string" || !node.label.isWellFormed()) throw new Error("Invalid node label");
    nodes.set(node.id, node);
    if (node.id.startsWith("feature:")) summaries.set(node.id, new Map());
  }
  const root = "source:" + sourceCommit;
  if (!nodes.has(root) || [...nodes.keys()].some((id) => id.startsWith("source:") && id !== root)) {
    throw new Error("Source root mismatch");
  }
  const fileNodes = [...nodes.values()].filter((node) => node.id.startsWith("file:"));
  if (fileNodes.length !== inventory.size ||
      fileNodes.some((node) => !inventory.has(node.source_file) || node.id !== "file:" + node.source_file)) {
    throw new Error("Source inventory does not match file nodes");
  }
  const referenced = new Set(inventory);
  const uniqueEdges = new Set();
  const featured = new Set();
  const inventoried = new Set();
  const inventoriedAnchors = new Set();
  const attachedAnchors = new Set();
  const implementations = [];
  for (const edge of graph.links) {
    if (!nodes.has(edge?.source) || !nodes.has(edge?.target)) throw new Error("Missing edge endpoint");
    const {source, target, relation, confidence_score, weight} = edge;
    if (!relations.has(relation) && !structuralRelations.has(relation)) {
      throw new Error("Unsupported evidence relation");
    }
    if (!Number.isFinite(confidence_score) || !Number.isFinite(weight)) throw new Error("Nonfinite evidence number");
    if (confidence_score < 0 || confidence_score > 1) throw new Error("Confidence score outside the unit interval");
    if (edge.confidence !== "EXTRACTED") throw new Error("Expected extracted evidence confidence");
    const identity = JSON.stringify([source, relation, target]);
    if (uniqueEdges.has(identity)) throw new Error("Duplicate evidence edge");
    uniqueEdges.add(identity);
    if (relation === "contains_source") {
      const path = nodes.get(target).source_file;
      if (source !== root || target !== "file:" + path || !inventory.has(path) || edge.source_file !== path) {
        throw new Error("Invalid source inventory edge");
      }
      inventoried.add(path);
    }
    if (relation === "contains_feature") {
      if (source !== root || !summaries.has(target)) throw new Error("Invalid source feature edge");
      featured.add(target);
    }
    if (relation === "located_in") {
      const origin = nodes.get(source);
      if (target !== "file:" + origin.source_file || !inventory.has(origin.source_file) ||
          edge.source_file !== origin.source_file || ![...relations].some((kind) => source.startsWith(kind + ":"))) {
        throw new Error("Invalid located_in evidence edge");
      }
      attachedAnchors.add(source);
    }
    if (relations.has(relation)) {
      if (!summaries.has(source) || !target.startsWith(relation + ":")) throw new Error("Invalid evidence anchor");
      if (relation === "implemented_in" && nodes.get(target).file_type !== "code") {
        throw new Error("Invalid implementation target category");
      }
      if (relation === "implemented_in") implementations.push(edge);
      const path = nodes.get(target).source_file;
      // Linked-only source paths have digests but no file nodes in the pinned producer.
      if (inventory.has(path)) inventoriedAnchors.add(target);
      referenced.add(path);
      const counts = summaries.get(edge.source);
      counts.set(edge.relation, (counts.get(edge.relation) ?? 0) + 1);
    }
  }
  if (featured.size !== summaries.size || inventoried.size !== inventory.size) {
    throw new Error("Missing source-root attachment");
  }
  for (const anchor of inventoriedAnchors) {
    if (!attachedAnchors.has(anchor)) throw new Error("Missing source-file attachment: " + anchor);
  }
  for (const path of referenced) {
    const digest = receipt.source_sha256[path];
    if (!repositoryPath(path) || typeof digest !== "string" || !digestPattern.test(digest)) {
      throw new Error("Invalid or missing source digest");
    }
    if (sourceBlobs !== undefined) {
      const blob = sourceBlobs.get(path);
      if (!(blob instanceof Uint8Array) || sha256(blob) !== digest) {
        throw new Error("Pinned source bytes do not match digest: " + path);
      }
    }
  }
  if (!receipt.feature_links || typeof receipt.feature_links !== "object" ||
      Array.isArray(receipt.feature_links) || Object.keys(receipt.feature_links).length !== summaries.size) {
    throw new Error("Feature summary mismatch");
  }
  for (const [id, counts] of summaries) {
    const claimed = receipt.feature_links[id];
    if (!claimed || typeof claimed !== "object" || Array.isArray(claimed) ||
        Object.keys(claimed).length !== counts.size ||
        [...counts].some(([relation, count]) => claimed[relation] !== count)) {
      throw new Error("Feature summary mismatch: " + id);
    }
  }
  const physicalLines = new Map();
  if (sourceBlobs !== undefined) {
    const requestedLines = new Map();
    for (const edge of implementations) {
      const location = matchedLocation(edge, nodes.get(edge.target));
      if (!location) throw new Error("Invalid implementation location: " + edge.target);
      const { path, line } = location;
      if (!requestedLines.has(path)) requestedLines.set(path, new Set());
      requestedLines.get(path).add(line);
    }
    for (const [path, requested] of requestedLines) {
      physicalLines.set(path, mapSourceLines(sourceBlobs.get(path), path, requested));
    }
  }
  return { nodes, links: graph.links, digest, physicalLines };
}

export function inspectHandoff(directory, { limits = {}, maximum = profile.max_bundle_bytes } = {}) {
  const hash = createHash("sha256").update(bundleHeader);
  const parts = new Map();
  const sourceBlobs = new Map();
  let remaining = maximum - bundleHeader.length;
  for (const [name, defaultLimit] of Object.entries(profile.files)) {
    let bytes;
    try {
      bytes = readBytes(join(directory, name), limits[name] ?? defaultLimit, remaining);
    } catch (error) {
      throw new Error("Cannot read " + name + ": " + (error.code ?? error.message));
    }
    const prefix = String(bytes.length) + "\n";
    remaining -= prefix.length + bytes.length;
    hash.update(prefix).update(bytes);
    parts.set(name, bytes);
    if (name.startsWith("source-blobs/")) sourceBlobs.set(name.slice("source-blobs/".length), bytes);
  }
  const source = parts.get("source.txt").toString("latin1");
  if (source.length !== 41 || !/^[a-f0-9]{40}\n$/.test(source)) throw new Error("Invalid handoff source pin");
  const graph = inspect((name) => parts.get(name), source.slice(0, -1), {
    repository: "example/graphify-fixture", producerVersion: profile.producer_version, sourceBlobs,
  });
  return { ...graph, bundleDigest: hash.digest("hex") };
}

function mapSourceLines(blob, path, requested) {
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(blob);
  } catch {
    throw new Error("Invalid UTF-8 in pinned source: " + path);
  }
  const coordinates = new Map();
  let producerLine = 1;
  let physicalLine = 1;
  let start = 0;
  // The pinned producer uses Python splitlines. A Git line advances only at LF.
  for (const boundary of text.matchAll(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/gu)) {
    if (requested.has(producerLine)) coordinates.set(producerLine, physicalLine);
    producerLine++;
    if (boundary[0].endsWith("\n")) physicalLine++;
    start = boundary.index + boundary[0].length;
  }
  if (start < text.length && requested.has(producerLine)) coordinates.set(producerLine, physicalLine);
  if (coordinates.size !== requested.size) throw new Error("Implementation line is outside the pinned source: " + path);
  return coordinates;
}

export function implementationLocation({ nodes, links, physicalLines }, feature, target) {
  const edge = links.find((link) => link.source === feature && link.target === target &&
    link.relation === "implemented_in");
  return citationLocation(edge, nodes.get(target), physicalLines);
}

export function implementationLocations({ nodes, links, physicalLines }, feature) {
  return links.filter(link => link.source === feature && link.relation === "implemented_in")
    .map(link => citationLocation(link, nodes.get(link.target), physicalLines));
}

function citationLocation(edge, node, physicalLines) {
  const location = matchedLocation(edge, node);
  if (!location) return null;
  const line = physicalLines?.get(location.path)?.get(location.line);
  if (line === undefined || line === location.line) return location;
  return { path: location.path, line, producer_line: location.line };
}

function matchedLocation(edge, node) {
  if (!edge || !repositoryPath(node?.source_file) || node.source_file !== edge.source_file ||
      typeof node.source_location !== "string" || node.source_location !== edge.source_location ||
      !/^L[1-9][0-9]*$/.test(node.source_location)) {
    return null;
  }
  const line = Number(node.source_location.slice(1));
  return Number.isSafeInteger(line) ? { path: node.source_file, line } : null;
}
