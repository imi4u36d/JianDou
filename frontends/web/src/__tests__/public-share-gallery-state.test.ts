import { describe, expect, it, vi } from "vitest";
import { usePublicShareGallery } from "@/components/home/usePublicShareGallery";
import type { PublicShareItem, PublicShareListResponse, PublicShareQuery } from "@/types";

function share(mediaType: "image" | "video", likedByMe = false): PublicShareItem {
  return {
    id: `${mediaType}-id`, shareId: `${mediaType}-share`, materialAssetId: "asset",
    sourceType: "material", sourceId: "source", ownerUserId: 1, authorName: "author",
    title: mediaType, mediaType, publicUrl: `/${mediaType}`, fileUrl: "", previewUrl: "",
    likeCount: likedByMe ? 1 : 0, likedByMe, sharedAt: "2026-01-01", updatedAt: "2026-01-01",
    status: "ACTIVE",
  };
}

function response(items: PublicShareItem[]): PublicShareListResponse {
  return { items, total: items.length, offset: 0, limit: 24, hasMore: false };
}

describe("public share gallery state", () => {
  it("loads media groups and synchronizes liked preview state", async () => {
    const image = share("image");
    const video = share("video");
    const fetch = vi.fn(async (query: PublicShareQuery = {}) =>
      response(query.type === "image" ? [image] : [video]),
    );
    const liked = { ...image, likedByMe: true, likeCount: 1 };
    const like = vi.fn(async (_shareId: string) => liked);
    const unlike = vi.fn(async (_shareId: string) => image);
    const state = usePublicShareGallery({ fetch, like, unlike, loadOnMount: false });

    await state.loadAll();
    state.openPreview(state.imageShares.value[0]);
    await state.toggleLike(state.previewItem.value!);

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(state.videoShares.value[0]).toEqual(video);
    expect(state.imageShares.value[0].likedByMe).toBe(true);
    expect(state.previewItem.value?.likeCount).toBe(1);
    expect(state.likeBusy.value).toBe(false);
  });
});
