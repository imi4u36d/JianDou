package com.jiandou.api.generation.application;

import java.util.List;
import java.util.Map;

public interface GenerationApplicationService {

    Map<String, Object> catalog();

    Map<String, Object> createRun(Map<String, Object> request);

    List<Map<String, Object>> listRuns(int limit);

    Map<String, Object> getRun(String runId);

    Map<String, Object> usage();
}
