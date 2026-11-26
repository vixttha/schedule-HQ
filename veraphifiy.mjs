import { execFileSync } from "node:child_process";
import { linkSync, lstatSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";
import {
  GRAPH_BYTES, PINNED_PRODUCER, RECEIPT_BYTES, implementationLocations, inspectEvidenceBytes,
  parseEvidenceObject, readBytes, repositoryPath, sha256,
} from "./test-vault/javascript/inspect-evidence.mjs";

const ARCHIVE_FORMAT = 1;
const TOOL_VERSION = "v0.0.9";
const SOURCE_BYTES = 8 * 1024 * 1024;
const ENTRY_BYTES = 40 * 1024 * 1024;
const COMMIT = /^[a-f0-9]{40}$/;
const DIGEST = /^[a-f0-9]{64}$/;
const PROJECT = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}$/;
const VERSION = /^v(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2,3}$/;

function projectKey(project) {
  return typeof project === "string" && PROJECT.test(project) ? project.toLowerCase() : null;
}

function requireIdentity(project, version) {
  if (!projectKey(project) || !VERSION.test(version ?? "") || version.length > 64) {
    throw new Error("Specify an exact owner/repository and a version such as v1.2.3");
  }
}

function entryPath(archive, project, version) {
  return join(archive, sha256(JSON.stringify([projectKey(project), version])) + ".json");
}

function readArchiveFile(path) {
  if (!lstatSync(path).isFile()) throw new Error("Archive entry must be a regular file");
  return readBytes(path, ENTRY_BYTES);
}

function git(checkout, args, maxBuffer = 32 * 1024) {
  return execFileSync("git", ["--no-replace-objects", "-C", checkout, ...args], {
    maxBuffer, timeout: 15_000, windowsHide: true, stdio: ["ignore", "pipe", "pipe"],
  });
}

function readGitBlobs(checkout, commit, manifest) {
  if (!COMMIT.test(commit ?? "") || git(checkout, ["cat-file", "-t", commit]).toString().trim() !== "commit") {
    throw new Error("Source must be a full commit SHA in the selected Git checkout");
  }
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    throw new Error("Invalid source inventory");
  }
  const blobs = [];
  let total = 0;
  for (const path of Object.keys(manifest).sort()) {
    if (!repositoryPath(path)) throw new Error("Invalid source path: " + path);
    const listing = git(checkout, ["ls-tree", "-r", "-z", "--full-tree", commit, "--", ":(literal)" + path]);
    const match = /^(100644|100755) blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(listing.toString("utf8"));
    if (!match || match[3] !== path) throw new Error("Not an ordinary committed source file: " + path);
    const size = Number(git(checkout, ["cat-file", "-s", match[2]]).toString().trim());
    if (!Number.isSafeInteger(size) || size < 0 || total + size > SOURCE_BYTES) {
      throw new Error("Source inventory exceeds the archive byte budget");
    }
    const bytes = git(checkout, ["cat-file", "blob", match[2]], Math.max(1, size));
    total += bytes.length;
    blobs.push([path, bytes.toString("base64")]);
  }
  return blobs;
}

function decodeBytes(value, budget) {
  if (typeof value !== "string" || value.length > Math.ceil(budget / 3) * 4) {
    throw new Error("Invalid or oversized encoded evidence");
  }
  const bytes = Buffer.from(value, "base64");
  if (bytes.length > budget || bytes.toString("base64") !== value) {
    throw new Error("Invalid or oversized encoded evidence");
  }
  return bytes;
}

function verifyEntry(entry, project, version) {
  if (entry.format !== ARCHIVE_FORMAT || projectKey(entry.project) !== projectKey(project) || entry.version !== version ||
      !COMMIT.test(entry.source ?? "") || !Array.isArray(entry.blobs)) {
    throw new Error("Archive entry does not match the selected project and version");
  }
  const graph = decodeBytes(entry.graph, GRAPH_BYTES);
  const receipt = decodeBytes(entry.receipt, RECEIPT_BYTES);
  if (sha256(receipt) !== entry.receipt_sha256) throw new Error("Receipt digest mismatch");
  const sourceBlobs = new Map();
  let remaining = SOURCE_BYTES;
  for (const item of entry.blobs) {
    if (!Array.isArray(item) || item.length !== 2 || !repositoryPath(item[0]) || sourceBlobs.has(item[0])) {
      throw new Error("Invalid or repeated source inventory path");
    }
    const bytes = decodeBytes(item[1], remaining);
    sourceBlobs.set(item[0], bytes);
    remaining -= bytes.length;
  }
  const inventory = parseEvidenceObject(receipt, "receipt.json").source_sha256;
  if (!inventory || Object.keys(inventory).length !== sourceBlobs.size ||
      [...sourceBlobs].some(([path, bytes]) => !Object.hasOwn(inventory, path) || sha256(bytes) !== inventory[path])) {
    throw new Error("Archived source inventory does not match the receipt");
  }
  const evidence = inspectEvidenceBytes(graph, receipt, entry.source, {
    repository: entry.project, producerVersion: PINNED_PRODUCER, sourceBlobs,
  });
  return { evidence, summary: {
    project: entry.project, version, source: entry.source, format: ARCHIVE_FORMAT,
    veraphifiy_version: TOOL_VERSION, producer: PINNED_PRODUCER,
    graph_sha256: evidence.digest, receipt_sha256: entry.receipt_sha256,
  } };
}

function importVersion(options) {
  const { archive, project, version, source, checkout, evidence } = options;
  for (const input of [source, checkout, evidence]) {
    if (!input) throw new Error("Import requires --source, --checkout and --evidence");
  }
  const graph = readBytes(join(evidence, "graph.json"), GRAPH_BYTES);
  const receipt = readBytes(join(evidence, "receipt.json"), RECEIPT_BYTES);
  const { repository, source_sha256: inventory } = parseEvidenceObject(receipt, "receipt.json");
  if (projectKey(repository) !== projectKey(project)) throw new Error("Evidence scope or repository mismatch");
  // Store the producer's spelling so a case-only alias imports the same bytes.
  inspectEvidenceBytes(graph, receipt, source, { repository, producerVersion: PINNED_PRODUCER });
  const entry = {
    format: ARCHIVE_FORMAT, project: repository, version, source,
    graph: graph.toString("base64"), receipt: receipt.toString("base64"), receipt_sha256: sha256(receipt),
    blobs: readGitBlobs(checkout, source, inventory),
  };
  const { summary } = verifyEntry(entry, project, version);
  const bytes = Buffer.from(JSON.stringify(entry) + "\n");
  if (bytes.length > ENTRY_BYTES) throw new Error("Archive entry exceeds the total byte budget");
  mkdirSync(archive, { recursive: true, mode: 0o700 });
  const staging = mkdtempSync(join(archive, ".import-"));
  try {
    const staged = join(staging, "entry.json");
    writeFileSync(staged, bytes, { flag: "wx", flush: true, mode: 0o600 });
    const destination = entryPath(archive, project, version);
    try {
      linkSync(staged, destination);
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      if (!readArchiveFile(destination).equals(bytes)) {
        throw new Error("An existing project version cannot be replaced");
      }
    }
  } finally {
    rmSync(staging, { recursive: true, force: true });
  }
  return { ...summary, archive_sha256: sha256(bytes) };
}

function readVersion(command, { archive, project, version, feature, source, "archive-sha256": expectedDigest }) {
  if (source !== undefined && !COMMIT.test(source)) throw new Error("Expected source must be a full commit SHA");
  if (expectedDigest !== undefined && !DIGEST.test(expectedDigest)) {
    throw new Error("Expected archive digest must be a lowercase SHA-256");
  }
  let bytes;
  try {
    bytes = readArchiveFile(entryPath(archive, project, version));
  } catch (error) {
    if (error.code === "ENOENT") throw new Error("Project version is not archived");
    throw error;
  }
  const digest = sha256(bytes);
  if (expectedDigest !== undefined && digest !== expectedDigest) throw new Error("Archive SHA-256 mismatch");
  const { evidence, summary } = verifyEntry(parseEvidenceObject(bytes, "archive entry"), project, version);
  if (source !== undefined && summary.source !== source) throw new Error("Archive source commit mismatch");
  const result = { ...summary, archive_sha256: digest };
  if (command === "verify") return result;
  if (!feature?.startsWith("feature:") || !evidence.nodes.has(feature)) {
    throw new Error("Feature is not present in the selected version");
  }
  return { ...result, feature, citations: implementationLocations(evidence, feature) };
}

const usage = "Usage: node veraphifiy.mjs <import|verify|lookup> --archive DIR --project OWNER/REPO --version vX.Y.Z\n"
  + "  import requires --source SHA --checkout DIR --evidence DIR\n"
  + "  lookup requires --feature feature:ID\n"
  + "  project casing is ignored for selection; results keep the receipt spelling\n"
  + "  verify and lookup accept --source SHA and --archive-sha256 HASH to check independently recorded pins";

try {
  const [command, ...args] = process.argv.slice(2);
  if (command === "--help") {
    console.log(usage);
  } else if (command === "--version") {
    console.log(TOOL_VERSION);
  } else {
    if (!["import", "verify", "lookup"].includes(command)) throw new Error(usage);
    const validOptions = {
      archive: { type: "string" }, project: { type: "string" }, version: { type: "string" },
      source: { type: "string" },
      ...(command === "import" ? { checkout: { type: "string" }, evidence: { type: "string" } } : {}),
      ...(command !== "import" ? { "archive-sha256": { type: "string" } } : {}),
      ...(command === "lookup" ? { feature: { type: "string" } } : {}),
    };
    const { values } = parseArgs({ args, options: validOptions });
    if (!values.archive) throw new Error("Specify an archive directory");
    requireIdentity(values.project, values.version);
    const result = command === "import" ? importVersion(values) : readVersion(command, values);
    console.log(JSON.stringify(result));
  }
} catch (error) {
  console.error("Veraphify: " + error.message);
  process.exitCode = 1;
}
