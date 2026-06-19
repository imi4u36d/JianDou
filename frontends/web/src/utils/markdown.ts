/**
 * Markdown相关工具方法。
 */
const HTML_ESCAPE_MAP: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

/**
 * 处理escapeHtml。
 * @param value 待处理的值
 */
function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (char) => HTML_ESCAPE_MAP[char] || char);
}

/**
 * 格式化内联。
 * @param value 待处理的值
 */
function formatInline(value: string) {
  const escaped = escapeHtml(value);
  return escaped
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>');
}

/**
 * 检查是否TableSeparator。
 * @param line line值
 */
function isTableSeparator(line: string) {
  return /^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*$/.test(line.trim());
}

/**
 * 解析Table。
 * @param lines lines值
 * @param startIndex start索引值
 */
function parseTable(lines: string[], startIndex: number) {
  const rows: string[][] = [];
  let index = startIndex;
  while (index < lines.length && lines[index].includes("|")) {
    rows.push(lines[index].trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim()));
    index += 1;
  }
  if (rows.length < 2) {
    return null;
  }
  const header = rows[0];
  const body = isTableSeparator(lines[startIndex + 1] || "") ? rows.slice(2) : rows.slice(1);
  const tableBody = body.length > 0 ? body : [];
  const headerHtml = header.map((cell) => `<th>${formatInline(cell)}</th>`).join("");
  const bodyHtml = tableBody
    .map((row) => `<tr>${row.map((cell) => `<td>${formatInline(cell)}</td>`).join("")}</tr>`)
    .join("");
  return {
    html: `<table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`,
    nextIndex: index,
  };
}

/**
 * 渲染Markdown转为Html。
 * @param markdown Markdown值
 */
export function renderMarkdownToHtml(markdown: string) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: string[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
      continue;
    }

    if (/^#{1,6}\s+/.test(trimmed)) {
      const level = Math.min(6, trimmed.match(/^#+/)?.[0].length ?? 1);
      const text = trimmed.replace(/^#{1,6}\s+/, "");
      blocks.push(`<h${level}>${formatInline(text)}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^>\s?/.test(trimmed)) {
      const quoteLines: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index].trim())) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(`<blockquote>${quoteLines.map((item) => `<p>${formatInline(item)}</p>`).join("")}</blockquote>`);
      continue;
    }

    if (trimmed.includes("|") && lines[index + 1] && isTableSeparator(lines[index + 1])) {
      const parsed = parseTable(lines, index);
      if (parsed) {
        blocks.push(parsed.html);
        index = parsed.nextIndex;
        continue;
      }
    }

    if (/^\s*([-*])\s+/.test(trimmed) || /^\s*\d+\.\s+/.test(trimmed)) {
      const ordered = /^\s*\d+\.\s+/.test(trimmed);
      const tag = ordered ? "ol" : "ul";
      const items: string[] = [];
      while (index < lines.length) {
        const current = lines[index].trim();
        if (!(ordered ? /^\s*\d+\.\s+/.test(current) : /^\s*[-*]\s+/.test(current))) {
          break;
        }
        items.push(current.replace(/^\s*(?:[-*]|\d+\.)\s+/, ""));
        index += 1;
      }
      blocks.push(`<${tag}>${items.map((item) => `<li>${formatInline(item)}</li>`).join("")}</${tag}>`);
      continue;
    }

    const paragraphLines: string[] = [trimmed];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^#{1,6}\s+/.test(lines[index].trim()) &&
      !/^>\s?/.test(lines[index].trim()) &&
      !lines[index].trim().startsWith("```") &&
      !(lines[index].trim().includes("|") && lines[index + 1] && isTableSeparator(lines[index + 1])) &&
      !/^\s*([-*])\s+/.test(lines[index].trim()) &&
      !/^\s*\d+\.\s+/.test(lines[index].trim())
    ) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    blocks.push(`<p>${formatInline(paragraphLines.join(" "))}</p>`);
  }

  return blocks.join("");
}

/**
 * 处理download文本文件。
 * @param fileName 文件Name值
 * @param content content值
 * @param mimeType mime类型值
 */
export function downloadTextFile(fileName: string, content: string, mimeType = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.rel = "noreferrer noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
