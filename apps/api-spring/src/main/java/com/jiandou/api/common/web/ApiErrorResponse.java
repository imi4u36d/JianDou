package com.jiandou.api.common.web;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.OffsetDateTime;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
public record ApiErrorResponse(
    String code,
    int status,
    String error,
    String message,
    String path,
    @JsonProperty("timestamp") OffsetDateTime timestamp
) {
}
