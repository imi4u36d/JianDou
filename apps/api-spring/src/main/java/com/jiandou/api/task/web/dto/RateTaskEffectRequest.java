package com.jiandou.api.task.web.dto;

/**
 * 任务效果评分请求体。
 */
public record RateTaskEffectRequest(
    Integer effectRating,
    String effectRatingNote
) {}
