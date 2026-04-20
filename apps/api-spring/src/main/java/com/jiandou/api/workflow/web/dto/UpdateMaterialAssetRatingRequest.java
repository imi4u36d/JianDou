package com.jiandou.api.workflow.web.dto;

public record UpdateMaterialAssetRatingRequest(
    Integer effectRating,
    String effectRatingNote
) {}
