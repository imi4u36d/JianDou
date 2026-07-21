import { afterEach, describe, expect, it, vi } from "vitest";
import { downloadMedia, inferMediaDownloadKind } from "@/utils/download";

const originalUserAgent = Object.getOwnPropertyDescriptor(window.navigator, "userAgent");
const originalMaxTouchPoints = Object.getOwnPropertyDescriptor(window.navigator, "maxTouchPoints");
const originalShare = Object.getOwnPropertyDescriptor(window.navigator, "share");

function setNavigatorValue(name: "userAgent" | "maxTouchPoints", value: string | number) {
  Object.defineProperty(window.navigator, name, { configurable: true, value });
}

afterEach(() => {
  vi.restoreAllMocks();
  delete window.JianDouNative;
  if (originalUserAgent) {
    Object.defineProperty(window.navigator, "userAgent", originalUserAgent);
  }
  if (originalMaxTouchPoints) {
    Object.defineProperty(window.navigator, "maxTouchPoints", originalMaxTouchPoints);
  }
  if (originalShare) {
    Object.defineProperty(window.navigator, "share", originalShare);
  } else {
    Reflect.deleteProperty(window.navigator, "share");
  }
});

describe("downloadMedia", () => {
  it("infers image and video media kinds from file extensions", () => {
    expect(inferMediaDownloadKind("/storage/frame.png")).toBe("image");
    expect(inferMediaDownloadKind("/storage/clip.mp4?sign=1")).toBe("video");
    expect(inferMediaDownloadKind("/storage/output")).toBe("file");
  });

  it("uses the browser download flow on desktop", async () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const originalCreateElement = document.createElement.bind(document);
    let createdLink: HTMLAnchorElement | undefined;
    vi.spyOn(document, "createElement").mockImplementation((tagName: string, options?: ElementCreationOptions) => {
      const element = originalCreateElement(tagName, options);
      if (tagName === "a") {
        createdLink = element as HTMLAnchorElement;
      }
      return element;
    });

    const result = await downloadMedia({ url: "/storage/tasks/result", title: "成片", mediaType: "video" });

    expect(result.target).toBe("browser");
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(createdLink).toBeDefined();
    const link = createdLink as HTMLAnchorElement;
    expect(link.download).toBe("成片.mp4");
    expect(link.target).toBe("_blank");
  });

  it("requests album permission and saves through the native bridge on mobile", async () => {
    setNavigatorValue("userAgent", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)");
    setNavigatorValue("maxTouchPoints", 5);
    const requestAlbumPermission = vi.fn(() => true);
    const saveMediaToAlbum = vi.fn(() => ({ success: true }));
    window.JianDouNative = { requestAlbumPermission, saveMediaToAlbum };

    const result = await downloadMedia({ url: "/storage/frame.png", title: "首帧", mediaType: "image" });

    expect(result.target).toBe("album");
    expect(requestAlbumPermission).toHaveBeenCalledTimes(1);
    expect(saveMediaToAlbum).toHaveBeenCalledWith(expect.objectContaining({
      fileName: "首帧.png",
      mediaType: "image",
      requestPermission: true,
      url: "http://localhost:3000/storage/frame.png",
    }));
  });

  it("stops when mobile album permission is denied", async () => {
    setNavigatorValue("userAgent", "Mozilla/5.0 (Linux; Android 14; Mobile)");
    setNavigatorValue("maxTouchPoints", 5);
    window.JianDouNative = {
      requestAlbumPermission: vi.fn(() => false),
      saveMediaToAlbum: vi.fn(() => true),
    };

    await expect(downloadMedia({ url: "/storage/frame.png", title: "首帧", mediaType: "image" })).rejects.toThrow("未获得相册权限");
  });

  it("falls back to browser download without invoking system sharing", async () => {
    setNavigatorValue("userAgent", "Mozilla/5.0 (Linux; Android 14; Mobile)");
    setNavigatorValue("maxTouchPoints", 5);
    const share = vi.fn(async () => undefined);
    Object.defineProperty(window.navigator, "share", { configurable: true, value: share });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    const result = await downloadMedia({ url: "/storage/frame.png", title: "首帧", mediaType: "image" });

    expect(result.target).toBe("browser");
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(share).not.toHaveBeenCalled();
  });
});
