package com.jiandou.api.generation;

import java.util.Map;

public record RemoteTaskQueryResult(
    String taskId,
    String status,
    String videoUrl,
    String message,
    Map<String, Object> payload
) {
}
