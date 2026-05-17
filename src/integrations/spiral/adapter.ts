import { mkdirSync, writeFileSync } from "node:fs";
import { execFile } from "node:child_process";
import { dirname } from "node:path";
import { promisify } from "node:util";
import type { NewsletterDraft } from "../../drafting/newsletterDraft.js";

export interface SpiralDraftAdapter {
  createDraft(prompt: string): Promise<NewsletterDraft>;
}

type SpiralGenerationMode = "instant" | "interactive";

interface SpiralCliDraft {
  title?: string;
  content?: string;
  url?: string;
}

interface SpiralCliResponse {
  status?: "needs_input" | "complete";
  messages?: string[];
  drafts?: SpiralCliDraft[];
  text?: string;
}

type CommandRunner = (
  command: string,
  args: string[],
  options: { maxBuffer: number; shell?: boolean }
) => Promise<{ stdout: string; stderr: string }>;

const execFileAsync = promisify(execFile);
const defaultRunner: CommandRunner = async (command, args, options) => execFileAsync(command, args, options);

export class ManualSpiralAdapter implements SpiralDraftAdapter {
  constructor(private readonly artifactPath: string) {}

  async createDraft(prompt: string): Promise<NewsletterDraft> {
    writeSpiralInputArtifact(this.artifactPath, prompt);
    return {
      title: "Manual Spiral Draft Needed",
      body: `Use the Spiral input artifact to generate the issue draft:\n\n${this.artifactPath}`
    };
  }
}

export class SpiralCliAdapter implements SpiralDraftAdapter {
  constructor(
    private readonly artifactPath: string,
    private readonly generationMode: SpiralGenerationMode = "instant",
    private readonly runner: CommandRunner = defaultRunner
  ) {}

  async createDraft(prompt: string): Promise<NewsletterDraft> {
    writeSpiralInputArtifact(this.artifactPath, prompt);

    const response = await this.runSpiral(prompt);
    const draft = response.drafts?.[0];
    if (!draft?.content) {
      if (response.status === "needs_input") {
        throw new Error(`Spiral requested more context: ${(response.messages ?? []).join(" ")}`);
      }

      throw new Error(response.text || "Spiral did not return a draft.");
    }

    const body = removeDuplicateTitleHeading(draft.content, draft.title);
    const sourceLink = draft.url ? `\n\n[View in Spiral](${draft.url})` : "";
    return {
      title: draft.title || "Houston Housing Dispatch",
      body: `${body}${sourceLink}`
    };
  }

  private async runSpiral(prompt: string): Promise<SpiralCliResponse> {
    const command = process.platform === "win32" ? "npx.cmd" : "npx";
    const args = [
      "@every-env/spiral-cli@latest",
      "write",
      "Write the Houston Housing Dispatch issue using the attached prompt.",
      "--file",
      this.artifactPath,
      "--json"
    ];
    if (this.generationMode === "instant") {
      args.push("--instant");
    }

    const result = await this.runner(command, args, {
      maxBuffer: 1024 * 1024 * 10,
      shell: process.platform === "win32"
    });
    return parseSpiralJson(result.stdout);
  }
}

function removeDuplicateTitleHeading(content: string, title?: string): string {
  if (!title) {
    return content;
  }

  const lines = content.split(/\r?\n/);
  const firstContentLine = lines.findIndex((line) => line.trim().length > 0);
  if (firstContentLine === -1) {
    return content;
  }

  if (lines[firstContentLine].trim() === `# ${title.trim()}`) {
    lines.splice(firstContentLine, 1);
    while (lines[firstContentLine]?.trim() === "") {
      lines.splice(firstContentLine, 1);
    }
    return lines.join("\n");
  }

  return content;
}

function writeSpiralInputArtifact(path: string, prompt: string): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, prompt, "utf8");
}

function parseSpiralJson(stdout: string): SpiralCliResponse {
  const trimmed = stdout.trim();
  try {
    return JSON.parse(trimmed) as SpiralCliResponse;
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start >= 0 && end > start) {
      return JSON.parse(trimmed.slice(start, end + 1)) as SpiralCliResponse;
    }
    throw new Error("Spiral CLI returned non-JSON output.");
  }
}
