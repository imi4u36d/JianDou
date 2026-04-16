package com.jiandou.api.task.domain;

import com.jiandou.api.generation.GenerationModelKinds;
import java.util.Locale;
import java.util.Set;

/**
 * 任务结果类型常量与判定。
 */
public final class TaskResultTypes {

    public static final String TEXT = GenerationModelKinds.TEXT;
    public static final String IMAGE = GenerationModelKinds.IMAGE;
    public static final String VIDEO = GenerationModelKinds.VIDEO;
    public static final String VIDEO_CLIP = "video_clip";
    public static final String VIDEO_JOIN = "video_join";
    public static final String JOIN_VIDEO = "join_video";
    public static final String JOINED_VIDEO = "joined_video";

    private static final Set<String> VIDEO_TYPES = Set.of(VIDEO, VIDEO_CLIP);
    private static final Set<String> JOIN_TYPES = Set.of(VIDEO_JOIN, JOIN_VIDEO, JOINED_VIDEO);

    private TaskResultTypes() {}

    public static boolean isVideo(Object raw) {
        return VIDEO_TYPES.contains(normalize(raw));
    }

    public static boolean isJoin(Object raw) {
        return JOIN_TYPES.contains(normalize(raw));
    }

    public static boolean isPrimaryVideo(Object raw) {
        return VIDEO.equals(normalize(raw));
    }

    public static String normalize(Object raw) {
        return raw == null ? "" : String.valueOf(raw).trim().toLowerCase(Locale.ROOT);
    }
}
