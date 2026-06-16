/**
 * 处理解析运行时URL。
 * @param input 输入值
 * @param baseUrl 基础 URL
 */
/**
 * URL相关工具方法。
 */
export function resolveRuntimeUrl(input: string | null | undefined, baseUrl: string) {
  if (!input) {
    return "";
  }

  if (/^(https?:)?\/\//.test(input) || input.startsWith("blob:") || input.startsWith("data:")) {
    return input;
  }

  if (input.startsWith("/")) {
    return new URL(input, document.baseURI).toString();
  }

  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  return new URL(input, normalizedBase).toString();
}
