const SECRET_PATTERNS = [
  /([A-Za-z0-9_]*TOKEN[A-Za-z0-9_]*=)[^\s]+/gi,
  /([A-Za-z0-9_]*SECRET[A-Za-z0-9_]*=)[^\s]+/gi,
  /(session(?:_token)?["']?\s*[:=]\s*["']?)[^"',\s]+/gi,
  /(refresh(?:_token)?["']?\s*[:=]\s*["']?)[^"',\s]+/gi
];

export function redact(value: string): string {
  return SECRET_PATTERNS.reduce((current, pattern) => current.replace(pattern, "$1[REDACTED]"), value);
}

export function redactObject<T>(value: T): T {
  return JSON.parse(redact(JSON.stringify(value))) as T;
}
