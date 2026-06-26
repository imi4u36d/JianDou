export type DownloadMediaKind = "image" | "video" | "file";

export interface MediaDownloadOptions {
  url?: string | null;
  title?: string | null;
  fileName?: string | null;
  mediaType?: DownloadMediaKind | null;
}

export interface MediaDownloadResult {
  target: "album" | "browser" | "share";
}

type NativeResult = boolean | string | number | { success?: boolean; granted?: boolean; status?: string; message?: string } | null | undefined;
type MaybePromise<T> = T | Promise<T>;

interface NativeAlbumBridge {
  requestAlbumPermission?: (payload: NativeAlbumPayload) => MaybePromise<NativeResult>;
  saveMediaToAlbum?: (payload: NativeAlbumPayload) => MaybePromise<NativeResult>;
}

interface AndroidAlbumBridge {
  requestAlbumPermission?: (payload: string) => NativeResult;
  saveMediaToAlbum?: (payload: string) => NativeResult;
}

interface NativeAlbumPayload {
  url: string;
  fileName: string;
  mediaType: "image" | "video";
  requestPermission: true;
}

declare global {
  interface Window {
    JianDouNative?: NativeAlbumBridge;
    Android?: AndroidAlbumBridge;
    webkit?: {
      messageHandlers?: Record<string, { postMessage: (payload: unknown) => void } | undefined>;
    };
  }
}

const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "gif", "webp", "avif", "bmp", "heic"]);
const VIDEO_EXTENSIONS = new Set(["mp4", "mov", "webm", "m4v", "avi", "mkv"]);

export async function downloadMedia(options: MediaDownloadOptions): Promise<MediaDownloadResult> {
  const url = String(options.url ?? "").trim();
  if (!url) {
    throw new Error("下载地址为空");
  }

  const mediaType = options.mediaType ?? inferMediaDownloadKind(url);
  const fileName = inferMediaFileName(url, options.fileName || options.title, mediaType);

  if (isMobileDevice() && (mediaType === "image" || mediaType === "video")) {
    const payload: NativeAlbumPayload = {
      url: toAbsoluteUrl(url),
      fileName,
      mediaType,
      requestPermission: true,
    };
    const savedToAlbum = await trySaveMediaToAlbum(payload);
    if (savedToAlbum) {
      return { target: "album" };
    }
    const shared = await tryShareMedia(payload);
    if (shared) {
      return { target: "share" };
    }
  }

  triggerBrowserDownload(url, fileName);
  return { target: "browser" };
}

export function inferMediaDownloadKind(url: string): DownloadMediaKind {
  const extension = extensionFromUrl(url);
  if (IMAGE_EXTENSIONS.has(extension)) return "image";
  if (VIDEO_EXTENSIONS.has(extension)) return "video";
  return "file";
}

export function isMobileDevice(): boolean {
  if (typeof navigator === "undefined") return false;
  const userAgent = navigator.userAgent || "";
  if (/Android|iPhone|iPad|iPod|Mobile|Windows Phone/i.test(userAgent)) return true;
  return /Macintosh/i.test(userAgent) && (navigator.maxTouchPoints ?? 0) > 1;
}

function triggerBrowserDownload(url: string, fileName: string) {
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

async function trySaveMediaToAlbum(payload: NativeAlbumPayload): Promise<boolean> {
  if (typeof window === "undefined") return false;

  const nativeBridge = window.JianDouNative;
  if (nativeBridge?.saveMediaToAlbum) {
    await assertAlbumPermission(nativeBridge.requestAlbumPermission?.(payload));
    return nativeResultAllows(await nativeBridge.saveMediaToAlbum(payload));
  }

  const androidBridge = window.Android;
  if (androidBridge?.saveMediaToAlbum) {
    const jsonPayload = JSON.stringify(payload);
    await assertAlbumPermission(androidBridge.requestAlbumPermission?.(jsonPayload));
    return nativeResultAllows(androidBridge.saveMediaToAlbum(jsonPayload));
  }

  const iosHandlers = window.webkit?.messageHandlers;
  const saveHandler = iosHandlers?.jiandouSaveMediaToAlbum;
  if (saveHandler) {
    iosHandlers?.jiandouRequestAlbumPermission?.postMessage(payload);
    saveHandler.postMessage(payload);
    return true;
  }

  return false;
}

async function assertAlbumPermission(result: MaybePromise<NativeResult>) {
  const resolved = await result;
  if (!nativeResultAllows(resolved)) {
    throw new Error("未获得相册权限，无法保存到相册");
  }
}

function nativeResultAllows(result: NativeResult): boolean {
  if (result == null) return true;
  if (typeof result === "boolean") return result;
  if (typeof result === "number") return result !== 0;
  if (typeof result === "string") {
    return !["0", "false", "denied", "cancel", "cancelled", "error", "failed"].includes(result.trim().toLowerCase());
  }
  if (typeof result.success === "boolean") return result.success;
  if (typeof result.granted === "boolean") return result.granted;
  if (typeof result.status === "string") return nativeResultAllows(result.status);
  return true;
}

async function tryShareMedia(payload: NativeAlbumPayload): Promise<boolean> {
  if (typeof navigator === "undefined" || typeof navigator.share !== "function" || typeof File === "undefined") {
    return false;
  }

  try {
    const response = await fetch(payload.url);
    if (!response.ok) return false;
    const blob = await response.blob();
    const type = blob.type || fallbackMimeType(payload.mediaType);
    const file = new File([blob], payload.fileName, { type });
    const shareData: ShareData = { files: [file], title: payload.fileName };
    if (typeof navigator.canShare === "function" && !navigator.canShare(shareData)) {
      return false;
    }
    await navigator.share(shareData);
    return true;
  } catch {
    return false;
  }
}

function inferMediaFileName(url: string, preferredName: string | null | undefined, mediaType: DownloadMediaKind): string {
  const extension = extensionFromUrl(url) || defaultExtension(mediaType);
  const fromPreferred = sanitizeFileName(preferredName || "");
  if (fromPreferred) {
    return hasFileExtension(fromPreferred) ? fromPreferred : `${fromPreferred}.${extension}`;
  }

  const fromUrl = sanitizeFileName(lastPathSegment(url));
  if (fromUrl) {
    return hasFileExtension(fromUrl) ? fromUrl : `${fromUrl}.${extension}`;
  }

  return `jiandou-${mediaType}-${Date.now()}.${extension}`;
}

function sanitizeFileName(value: string): string {
  return value.replace(/[\\/:*?"<>|]+/g, "-").replace(/\s+/g, " ").trim().slice(0, 120);
}

function hasFileExtension(fileName: string): boolean {
  return /\.[a-z0-9]{2,8}$/i.test(fileName);
}

function extensionFromUrl(url: string): string {
  const parts = lastPathSegment(url).split(".");
  if (parts.length < 2) return "";
  return parts.pop()?.toLowerCase() || "";
}

function lastPathSegment(url: string): string {
  try {
    return decodeURIComponent(new URL(url, window.location.origin).pathname.split("/").filter(Boolean).pop() || "");
  } catch {
    return decodeURIComponent(url.split("?")[0]?.split("#")[0]?.split("/").filter(Boolean).pop() || "");
  }
}

function defaultExtension(mediaType: DownloadMediaKind): string {
  if (mediaType === "image") return "png";
  if (mediaType === "video") return "mp4";
  return "download";
}

function fallbackMimeType(mediaType: "image" | "video"): string {
  return mediaType === "image" ? "image/png" : "video/mp4";
}

function toAbsoluteUrl(url: string): string {
  try {
    return new URL(url, window.location.origin).toString();
  } catch {
    return url;
  }
}
