export function resolveRuntimeUrl(input: string | null | undefined, baseUrl: string) {
  if (!input) {
    return "";
  }

  if (/^(https?:)?\/\//.test(input) || input.startsWith("blob:") || input.startsWith("data:")) {
    return input;
  }

  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedInput = input.startsWith("/") ? input.slice(1) : input;
  return new URL(normalizedInput, normalizedBase).toString();
}
