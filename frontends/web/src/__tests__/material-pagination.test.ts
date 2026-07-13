import { describe, expect, it, vi } from "vitest";
import { useMaterialPagination } from "@/composables/materials/useMaterialPagination";
import type { MaterialAssetLibraryItem, MaterialAssetPage } from "@/types";

function asset(id: string): MaterialAssetLibraryItem {
  return { id, title: id, mediaType: "image", publicUrl: `/${id}.png` } as MaterialAssetLibraryItem;
}

function page(items: MaterialAssetLibraryItem[], hasMore: boolean, nextOffset: number | null): MaterialAssetPage {
  return { items, offset: 0, limit: 2, total: items.length, hasMore, nextOffset };
}

describe("material pagination", () => {
  it("replaces, appends and de-duplicates asset pages", async () => {
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(page([asset("a"), asset("b")], true, 2))
      .mockResolvedValueOnce(page([asset("b"), asset("c")], false, null));
    const cacheAssets = vi.fn();
    const pagination = useMaterialPagination({
      fetchPage,
      buildQuery: (offset) => ({ offset, limit: 2 }),
      cacheAssets,
      onError: vi.fn(),
    });

    expect(await pagination.loadAssets()).toBe(true);
    expect(await pagination.loadMoreAssets()).toBe(true);

    expect(pagination.assets.value.map((item) => item.id)).toEqual(["a", "b", "c"]);
    expect(fetchPage).toHaveBeenNthCalledWith(2, { offset: 2, limit: 2 });
    expect(pagination.hasMoreAssets.value).toBe(false);
    expect(cacheAssets).toHaveBeenCalledTimes(2);
  });

  it("ignores a stale first-page response", async () => {
    let resolveFirst!: (value: MaterialAssetPage) => void;
    let resolveSecond!: (value: MaterialAssetPage) => void;
    const fetchPage = vi
      .fn()
      .mockImplementationOnce(() => new Promise<MaterialAssetPage>((resolve) => (resolveFirst = resolve)))
      .mockImplementationOnce(() => new Promise<MaterialAssetPage>((resolve) => (resolveSecond = resolve)));
    const pagination = useMaterialPagination({
      fetchPage,
      buildQuery: (offset) => ({ offset, limit: 2 }),
      cacheAssets: vi.fn(),
      onError: vi.fn(),
    });

    const firstLoad = pagination.loadAssets();
    const secondLoad = pagination.loadAssets();
    resolveSecond(page([asset("new")], false, null));
    await secondLoad;
    resolveFirst(page([asset("stale")], false, null));
    await firstLoad;

    expect(pagination.assets.value.map((item) => item.id)).toEqual(["new"]);
  });

  it("clears pagination state and invalidates active requests", () => {
    const pagination = useMaterialPagination({
      fetchPage: vi.fn(),
      buildQuery: (offset) => ({ offset }),
      cacheAssets: vi.fn(),
      onError: vi.fn(),
    });
    pagination.assets.value = [asset("a")];
    pagination.hasMoreAssets.value = true;

    pagination.clearAssets();

    expect(pagination.assets.value).toEqual([]);
    expect(pagination.hasMoreAssets.value).toBe(false);
  });
});
