package com.jiandou.api.generation.text;

import java.util.Map;

public record PreparedTextModelRequest(
    String endpoint,
    Map<String, Object> body,
    boolean responsesApi
) {}
