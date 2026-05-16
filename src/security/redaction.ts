const SECRET_PATTERNS = [
  /([A-Za-z0-9_]*TOKEN[A-Za-z0-9_]*=)[^\s]+/gi,
  /([A-Za-z0-9_]*SECRET[A-Za-z0-9_]*=)[^\s]+/gi,
  /(session(?:_token)?["']?\s*[:=]\s*["']?)[^"',\s]+/gi,
  /(refresh(?:_token)?["']?\s*[:=]\s*["']?)[^"',\s]+/gi,
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
  /\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g
];

export function redact(value: string): string {
  return SECRET_PATTERNS.reduce((current, pattern) => current.replace(pattern, redactMatch), value);
}

export function redactObject<T>(value: T): T {
  return JSON.parse(redact(JSON.stringify(value))) as T;
}

function redactMatch(match: string, prefix?: string): string {
  return typeof prefix === "string" ? `${prefix}[REDACTED]` : "[REDACTED]";
}
