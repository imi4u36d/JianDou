export type QueryValue = string | number | boolean | null | undefined;
export type QueryValues = Readonly<Record<string, QueryValue>>;

/**
 * Serialize optional query values consistently across API modules.
 *
 * Empty strings, null, and undefined are omitted. String values are trimmed;
 * numeric zero and boolean false are intentionally preserved.
 */
export function buildQueryString(values: QueryValues): string {
  const params = new URLSearchParams();

  for (const [key, rawValue] of Object.entries(values)) {
    if (rawValue === null || rawValue === undefined) {
      continue;
    }

    if (typeof rawValue === "string") {
      const value = rawValue.trim();
      if (!value) {
        continue;
      }
      params.set(key, value);
      continue;
    }

    params.set(key, String(rawValue));
  }

  return params.toString();
}

/** Append a serialized query string only when at least one value is present. */
export function withQuery(path: string, values: QueryValues): string {
  const query = buildQueryString(values);
  return query ? `${path}?${query}` : path;
}
