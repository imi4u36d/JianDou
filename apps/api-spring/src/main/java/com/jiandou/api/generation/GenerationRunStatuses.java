package com.jiandou.api.generation;

import java.util.Locale;
import java.util.Set;

/**
 * 生成运行状态常量与判定。
 */
public final class GenerationRunStatuses {

    public static final String QUEUED = "queued";
    public static final String SUBMITTED = "submitted";
    public static final String RUNNING = "running";
    public static final String ACCEPTED = "accepted";
    public static final String SUCCEEDED = "succeeded";
    public static final String FAILED = "failed";
    public static final String COMPLETED = "completed";
    public static final String SUCCESS = "success";

    private static final Set<String> ACTIVE = Set.of(ACCEPTED, QUEUED, SUBMITTED, RUNNING);
    private static final Set<String> SUCCESSFUL = Set.of(SUCCEEDED, COMPLETED, SUCCESS);

    private GenerationRunStatuses() {}

    public static boolean isActive(String raw) {
        return ACTIVE.contains(normalize(raw));
    }

    public static boolean isSuccessful(String raw) {
        return SUCCESSFUL.contains(normalize(raw));
    }

    public static String normalize(String raw) {
        return raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
    }
}
