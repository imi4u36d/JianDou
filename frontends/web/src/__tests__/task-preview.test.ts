import { describe, expect, it } from "vitest";
import type { TaskDetail, TaskOutput } from "@/types";
import { resolveTaskPreviewMedia, taskOutputUrl } from "@/utils/task-preview";

function task(overrides: Partial<TaskDetail>): TaskDetail {
  return {
    id: "task_1",
    taskType: "video_generation",
    title: "测试任务",
    status: "COMPLETED",
    progress: 100,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    sourceFileName: "",
    aspectRatio: "16:9",
    minDurationSeconds: 0,
    maxDurationSeconds: 0,
    introTemplate: "",
    outroTemplate: "",
    outputs: [],
    ...overrides,
  } as TaskDetail;
}

function output(overrides: Partial<TaskOutput>): TaskOutput {
  return {
    clipIndex: 1,
    title: "结果",
    reason: "",
    startSeconds: 0,
    endSeconds: 0,
    durationSeconds: 0,
    ...overrides,
  };
}

describe("resolveTaskPreviewMedia", () => {
  it("prefers joined video output for video tasks", () => {
    const preview = resolveTaskPreviewMedia(task({
      outputs: [
        output({ resultType: "image", previewUrl: "/storage/keyframe.png" }),
        output({ resultType: "video_generation", clipIndex: 2, previewUrl: "/storage/clip-2.mp4" }),
        output({ resultType: "video_join", clipIndex: 10002, downloadPath: "/storage/join-2.mp4" }),
      ],
    }));

    expect(preview).toMatchObject({ type: "video", url: "/storage/join-2.mp4" });
  });

  it("uses repository path fields for historical image outputs", () => {
    const preview = resolveTaskPreviewMedia(task({
      taskType: "image_generation",
      requestSnapshot: { taskType: "image_generation" },
      outputs: [
        output({ resultType: "image", previewPath: "/storage/workspace-image.png" }),
      ],
    }));

    expect(preview).toMatchObject({ type: "image", url: "/storage/workspace-image.png" });
  });

  it("uses original image result urls instead of thumbnails for task detail previews", () => {
    const preview = resolveTaskPreviewMedia(task({
      taskType: "image_generation",
      requestSnapshot: { taskType: "image_generation" },
      outputs: [
        output({
          resultType: "image",
          previewUrl: "/storage/thumbs/workspace-image.jpg",
          thumbnailUrl: "/storage/thumbs/workspace-image.jpg",
          downloadUrl: "/storage/workspace-image.png",
        }),
      ],
    }));

    expect(preview).toMatchObject({ type: "image", url: "/storage/workspace-image.png" });
  });

  it("uses linked material originals ahead of image output thumbnails", () => {
    const preview = resolveTaskPreviewMedia(task({
      taskType: "image_generation",
      requestSnapshot: { taskType: "image_generation" },
      outputs: [
        output({
          resultType: "image",
          materialAssetId: "asset_image",
          previewUrl: "/storage/thumbs/asset-image.jpg",
        }),
      ],
      materials: [
        {
          id: "asset_image",
          kind: "output",
          mediaType: "image",
          title: "图片结果",
          publicUrl: "/storage/asset-image.png",
          fileUrl: "/storage/asset-image.png",
          thumbnailUrl: "/storage/thumbs/asset-image.jpg",
        },
      ],
    }));

    expect(preview).toMatchObject({
      type: "image",
      url: "/storage/asset-image.png",
      materialAssetId: "asset_image",
    });
  });

  it("treats workspace image result types as image previews even without an image extension", () => {
    const preview = resolveTaskPreviewMedia(task({
      taskType: "image_to_image",
      requestSnapshot: { taskType: "image_to_image" },
      outputs: [
        output({ resultType: "image_to_image", downloadPath: "/storage/tasks/task_1/result" }),
      ],
    }));

    expect(preview).toMatchObject({ type: "image", url: "/storage/tasks/task_1/result" });
  });

  it("uses delayed workspace image urls from execution context", () => {
    const preview = resolveTaskPreviewMedia(task({
      taskType: "image_generation",
      requestSnapshot: { taskType: "image_generation" },
      outputs: [],
      executionContext: {
        latestImageOutputUrl: "/storage/tasks/task_1/workspace-image.png",
      },
    }));

    expect(preview).toMatchObject({ type: "image", url: "/storage/tasks/task_1/workspace-image.png" });
  });

  it("does not let source materials replace a generated output", () => {
    const preview = resolveTaskPreviewMedia(task({
      outputs: [
        output({ resultType: "video", previewUrl: "/storage/clip-1.mp4", thumbnailUrl: "/storage/clip-1.jpg" }),
      ],
      materials: [
        {
          id: "source_1",
          kind: "source",
          mediaType: "image",
          title: "输入图",
          fileUrl: "/storage/source.png",
          previewUrl: "/storage/source.png",
        },
      ],
    }));

    expect(preview).toMatchObject({
      type: "video",
      url: "/storage/clip-1.mp4",
      posterUrl: "/storage/clip-1.jpg",
    });
  });

  it("falls back to monitoring join output when detailed outputs are unavailable", () => {
    const preview = resolveTaskPreviewMedia(task({
      outputs: [],
      monitoring: {
        latestJoinName: "join-3",
        latestJoinOutputUrl: "/storage/join-3.mp4",
      },
    }));

    expect(preview).toMatchObject({ type: "video", url: "/storage/join-3.mp4", title: "join-3" });
  });

  it("keeps video monitoring output ahead of keyframe images for video tasks", () => {
    const preview = resolveTaskPreviewMedia(task({
      outputs: [
        output({ resultType: "image", previewUrl: "/storage/keyframe-only.png" }),
      ],
      monitoring: {
        latestJoinName: "join-1",
        latestJoinOutputUrl: "/storage/join-1.mp4",
      },
    }));

    expect(preview).toMatchObject({ type: "video", url: "/storage/join-1.mp4" });
  });

  it("uses linked material thumbnails as video posters", () => {
    const preview = resolveTaskPreviewMedia(task({
      outputs: [
        output({
          resultType: "video_join",
          clipIndex: 10006,
          materialAssetId: "asset_join",
          previewPath: "/storage/join-6.mp4",
        }),
      ],
      materials: [
        {
          id: "asset_join",
          kind: "video_join",
          mediaType: "video",
          title: "完整视频",
          fileUrl: "/storage/join-6.mp4",
          thumbnailUrl: "/storage/thumbs/join-6.jpg",
        },
      ],
    }));

    expect(preview).toMatchObject({
      type: "video",
      url: "/storage/join-6.mp4",
      posterUrl: "/storage/thumbs/join-6.jpg",
      materialAssetId: "asset_join",
    });
  });

  it("uses linked material publicUrl instead of previewUrl for media", () => {
    const preview = resolveTaskPreviewMedia(task({
      outputs: [
        output({
          resultType: "video_join",
          clipIndex: 10008,
          materialAssetId: "asset_public_join",
        }),
      ],
      materials: [
        {
          id: "asset_public_join",
          kind: "video_join",
          mediaType: "video",
          title: "完整视频",
          publicUrl: "/storage/join-public.mp4",
          fileUrl: "",
          previewUrl: "/storage/thumbs/join-public.jpg",
          thumbnailUrl: "/storage/thumbs/join-public.jpg",
        },
      ],
    }));

    expect(preview).toMatchObject({
      type: "video",
      url: "/storage/join-public.mp4",
      posterUrl: "/storage/thumbs/join-public.jpg",
      materialAssetId: "asset_public_join",
    });
  });

  it("uses linked material media when output only has materialAssetId", () => {
    const preview = resolveTaskPreviewMedia(task({
      outputs: [
        output({
          resultType: "video_join",
          clipIndex: 10007,
          materialAssetId: "asset_join_only",
        }),
      ],
      materials: [
        {
          id: "asset_join_only",
          kind: "video_join",
          mediaType: "video",
          title: "完整视频",
          fileUrl: "/storage/join-only.mp4",
          thumbnailUrl: "/storage/thumbs/join-only.jpg",
        },
      ],
    }));

    expect(preview).toMatchObject({
      type: "video",
      url: "/storage/join-only.mp4",
      posterUrl: "/storage/thumbs/join-only.jpg",
      materialAssetId: "asset_join_only",
    });
  });
});

describe("taskOutputUrl", () => {
  it("accepts both url and path shaped output fields", () => {
    expect(taskOutputUrl(output({ previewPath: "/storage/preview.png" }))).toBe("/storage/preview.png");
    expect(taskOutputUrl(output({ downloadPath: "/storage/download.mp4" }))).toBe("/storage/download.mp4");
  });
});
