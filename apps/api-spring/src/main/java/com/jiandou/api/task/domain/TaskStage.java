package com.jiandou.api.task.domain;

/**
 * 任务执行阶段枚举。
 */
public enum TaskStage {
    API("api"),
    ANALYSIS("analysis"),
    PLANNING("planning"),
    RENDER("render"),
    DISPATCH("dispatch"),
    FEEDBACK("feedback"),
    PIPELINE("pipeline"),
    PAUSED("paused");

    private final String code;

    TaskStage(String code) {
        this.code = code;
    }

    public String code() {
        return code;
    }
}
