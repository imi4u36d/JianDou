package com.jiandou.api.task.runtime;

import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.application.TaskStoryboardPlanner;
import com.jiandou.api.task.application.TaskExecutionCoordinator;
import com.jiandou.api.task.application.port.TaskQueuePort;
import com.jiandou.api.task.domain.ExecutionMode;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.domain.TaskStage;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.exception.TaskExecutionAbortedException;
import com.jiandou.api.task.persistence.TaskRepository;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.context.annotation.DependsOn;
import org.springframework.stereotype.Component;

/**
 * 任务工作节点流水线处理器。
 */
@Component
@DependsOn("databaseSchemaReady")
public class TaskWorkerPipelineHandler {

    private final TaskRepository taskRepository;
    private final TaskQueuePort taskQueuePort;
    private final TaskExecutionCoordinator executionCoordinator;
    private final GenerationApplicationService generationApplicationService;
    private final TaskExecutionRuntimeSupport runtimeSupport;
    private final TaskExecutionArtifactAssembler artifactAssembler;
    private final TaskStoryboardPlanner storyboardPlanner;
    private final TaskWorkerStatusStageService statusStageService;
    private final TaskWorkerRenderStageService renderStageService;
    private final TaskWorkerJoinStageService joinStageService;

    /**
     * 创建新的任务工作节点流水线处理器。
     * @param taskRepository 任务仓储值
     * @param taskQueuePort 任务队列端口值
     * @param executionCoordinator 执行协调器值
     * @param generationApplicationService 生成应用服务值
     * @param runtimeSupport 运行时支持值
     * @param artifactAssembler 产物Assembler值
     * @param storyboardPlanner 分镜规划器值
     * @param statusStageService 状态阶段服务值
     * @param renderStageService render阶段服务值
     * @param joinStageService 拼接阶段服务值
     */
    public TaskWorkerPipelineHandler(
        TaskRepository taskRepository,
        TaskQueuePort taskQueuePort,
        TaskExecutionCoordinator executionCoordinator,
        GenerationApplicationService generationApplicationService,
        TaskExecutionRuntimeSupport runtimeSupport,
        TaskExecutionArtifactAssembler artifactAssembler,
        TaskStoryboardPlanner storyboardPlanner,
        TaskWorkerStatusStageService statusStageService,
        TaskWorkerRenderStageService renderStageService,
        TaskWorkerJoinStageService joinStageService
    ) {
        this.taskRepository = taskRepository;
        this.taskQueuePort = taskQueuePort;
        this.executionCoordinator = executionCoordinator;
        this.generationApplicationService = generationApplicationService;
        this.runtimeSupport = runtimeSupport;
        this.artifactAssembler = artifactAssembler;
        this.storyboardPlanner = storyboardPlanner;
        this.statusStageService = statusStageService;
        this.renderStageService = renderStageService;
        this.joinStageService = joinStageService;
    }

    /**
     * 处理process任务。
     * @param taskId 任务标识
     * @param workerInstanceId 工作节点实例标识
     * @param workerType 工作节点类型值
     * @param executionMode 执行模式值
     */
    public void processTask(String taskId, String workerInstanceId, String workerType, String executionMode) {
        TaskWorkerExecutionContext runContext = new TaskWorkerExecutionContext(
            workerInstanceId,
            workerType,
            executionMode
        );
        processTask(taskId, runContext);
    }

    public void processTask(String taskId, String workerInstanceId, String workerType, ExecutionMode executionMode) {
        TaskWorkerExecutionContext runContext = new TaskWorkerExecutionContext(workerInstanceId, workerType, executionMode);
        processTask(taskId, runContext);
    }

    private void processTask(String taskId, TaskWorkerExecutionContext runContext) {
        TaskRecord task = taskRepository.findById(taskId);
        if (task == null) {
            taskQueuePort.remove(taskId);
            return;
        }
        if (!TaskStatus.PENDING.matches(task.status())) {
            taskQueuePort.remove(taskId);
            return;
        }
        try {
            taskQueuePort.remove(task.id());
            task.setQueued(false);
            task.setQueuePosition(null);
            if (task.startedAt() == null || task.startedAt().isBlank()) {
                task.setStartedAt(nowIso());
            }
            runtimeSupport.assertTaskStillActive(task);
            Map<String, Object> activeAttempt = runtimeSupport.activeAttempt(task);
            int[] dimensions = runtimeSupport.resolveDimensions(task);
            int durationSeconds = runtimeSupport.resolveDurationSeconds(task);
            String videoSize = dimensions[0] + "*" + dimensions[1];
            List<Integer> existingVideoClipIndices = existingVideoClipIndices(task);
            int completedClipCount = lastContiguousCompletedClipIndex(existingVideoClipIndices);
            int renderStartIndex = Math.max(1, completedClipCount + 1);
            String requestedResumeStage = stringValue(activeAttempt == null ? null : activeAttempt.get("resumeFromStage"));
            int requestedResumeClipIndex = intValue(activeAttempt == null ? null : activeAttempt.get("resumeFromClipIndex"), renderStartIndex);
            boolean reuseStoryboard = !requestedResumeStage.isBlank() || completedClipCount > 0;
            putExecutionContext(task, "durationSeconds", durationSeconds);
            putExecutionContext(task, "videoSize", videoSize);
            putExecutionContext(task, "workerInstanceId", runContext.workerInstanceId());
            putExecutionContext(task, "resumeExistingClipIndices", existingVideoClipIndices);
            putExecutionContext(task, "resumeExistingOutputCount", completedClipCount);
            putExecutionContext(task, "resumeRenderFromClipIndex", renderStartIndex);
            putExecutionContext(task, "attemptResumeFromStage", requestedResumeStage);
            putExecutionContext(task, "attemptResumeFromClipIndex", requestedResumeClipIndex);
            taskRepository.save(task);

            executionCoordinator.markActiveAttemptRunning(task, runContext.workerInstanceId());
            runtimeSupport.assertTaskStillActive(task);
            Map<String, Object> scriptRun = Map.of();
            String storyboardMarkdown;
            if (reuseStoryboard && task.storyboardScript() != null && !task.storyboardScript().isBlank()) {
                storyboardMarkdown = task.storyboardScript();
                executionCoordinator.recordTrace(task, TaskStage.ANALYSIS.code(), "analysis.reused", "检测到已有分镜脚本，跳过分析并继续后续镜头。", "INFO", Map.of(
                    "completedClipCount", completedClipCount,
                    "renderStartIndex", renderStartIndex,
                    "resumeFromStage", requestedResumeStage,
                    "resumeFromClipIndex", requestedResumeClipIndex
                ));
            } else {
                statusStageService.updateStatus(task, runContext, TaskStatus.ANALYZING.value(), 10, TaskStage.ANALYSIS.code(), "task.analyzing", "任务开始分析文本与镜头约束。");

                Map<String, Object> scriptRequest = runtimeSupport.buildScriptRunRequest(task);
                scriptRun = generationApplicationService.createRun(scriptRequest);
                runtimeSupport.assertTaskStillActive(task);
                Map<String, Object> scriptResult = resultMap(scriptRun);
                storyboardMarkdown = stringValue(scriptResult.get("scriptMarkdown"));
                if (storyboardMarkdown.isBlank()) {
                    throw new IllegalStateException("分镜脚本为空，未生成有效输出。");
                }
                task.setStoryboardScript(storyboardMarkdown);
                putExecutionContext(task, "analysisRunId", stringValue(scriptRun.get("id")));
                putExecutionContext(task, "scriptRunId", stringValue(scriptRun.get("id")));
                putExecutionContext(task, "analysisScriptText", storyboardMarkdown);
                putExecutionContext(task, "analysisPrompt", stringValue(scriptResult.get("prompt")));
                taskRepository.save(task);
                statusStageService.recordStageRun(
                    task,
                    runContext,
                    1,
                    TaskStage.ANALYSIS.code(),
                    1,
                    Map.of("title", task.title(), "aspectRatio", task.aspectRatio()),
                    Map.of("summary", "文本分析完成", "scriptRunId", stringValue(scriptRun.get("id")))
                );
                Map<String, Object> analysisModelCall = statusStageService.createModelCall(task, TaskStage.ANALYSIS.code(), "generation.script", scriptRequest, scriptRun, scriptResult, 1, "script");
                executionCoordinator.recordModelCall(task, analysisModelCall);
                statusStageService.recordRunCallChain(task, TaskStage.ANALYSIS.code(), scriptRun, scriptResult);
                Map<String, Object> scriptMaterial = artifactAssembler.createTextMaterial(task, scriptRun, scriptResult);
                executionCoordinator.recordMaterial(task, scriptMaterial);
                putExecutionContext(task, "storyboardFileUrl", stringValue(scriptMaterial.get("fileUrl")));
                taskRepository.save(task);
            }

            List<TaskStoryboardPlanner.StoryboardShotPlan> shotPlans = storyboardPlanner.buildStoryboardShotPlans(task, storyboardMarkdown);
            int storyboardClipCount = shotPlans.size();
            int requestedOutputCount = storyboardPlanner.resolveRequestedOutputCount(task, storyboardClipCount);
            if (requestedOutputCount < shotPlans.size()) {
                shotPlans = new ArrayList<>(shotPlans.subList(0, requestedOutputCount));
            }
            List<String> clipPrompts = shotPlans.stream().map(TaskStoryboardPlanner.StoryboardShotPlan::videoPrompt).toList();
            List<int[]> storyboardDurationRanges = storyboardPlanner.extractStoryboardShotDurationRanges(storyboardMarkdown);
            List<int[]> clipDurationPlan = storyboardPlanner.buildClipDurationPlan(task, durationSeconds, clipPrompts.size(), storyboardMarkdown);
            clipDurationPlan = storyboardPlanner.normalizeClipDurationPlan(task.requestSnapshot() == null ? "" : task.requestSnapshot().videoModel(), clipDurationPlan);
            putExecutionContext(task, "storyboardClipCount", storyboardClipCount);
            putExecutionContext(task, "requestedOutputCount", storyboardPlanner.requestSnapshotOutputCount(task));
            putExecutionContext(task, "plannedClipCount", clipPrompts.size());
            putExecutionContext(task, "clipPrompts", clipPrompts);
            putExecutionContext(task, "clipDurationPlan", storyboardPlanner.buildClipDurationPlanContext(clipDurationPlan, storyboardDurationRanges));
            taskRepository.save(task);
            executionCoordinator.recordTrace(task, TaskStage.PLANNING.code(), "planning.shots_resolved", "已完成分镜数量解析，按镜头顺序生成。", "INFO", Map.of(
                "clipCount", clipPrompts.size(),
                "storyboardClipCount", storyboardClipCount,
                "requestedOutputCount", storyboardPlanner.requestSnapshotOutputCount(task),
                "completedClipCount", completedClipCount,
                "renderStartIndex", renderStartIndex,
                "durationPlan", storyboardPlanner.buildClipDurationPlanContext(clipDurationPlan, storyboardDurationRanges)
            ));

            statusStageService.updateStatus(task, runContext, TaskStatus.PLANNING.value(), 35, TaskStage.PLANNING.code(), "task.planning", "任务开始按分镜生成关键画面。");
            TaskWorkerRenderStageService.RenderStageResult renderResult = renderStageService.render(
                task,
                runContext,
                new TaskWorkerRenderStageService.RenderStageRequest(
                    reuseStoryboard,
                    renderStartIndex,
                    completedClipCount,
                    requestedResumeStage,
                    requestedResumeClipIndex,
                    existingVideoClipIndices,
                    shotPlans,
                    clipDurationPlan,
                    dimensions[0],
                    dimensions[1],
                    durationSeconds,
                    videoSize,
                    resolveResumeLastFrameUrl(task, completedClipCount)
                )
            );
            statusStageService.completeTask(
                task,
                runContext,
                scriptRun,
                renderResult.imageRunIds(),
                renderResult.videoRunIds(),
                renderResult.clipCount(),
                renderResult.latestVideoOutputUrl()
            );
            // 补触发一次 join，覆盖 resume/no-op render 场景下的状态门控窗口。
            joinStageService.scheduleJoin(task);
        } catch (TaskExecutionAbortedException ex) {
            statusStageService.handleAbort(task, runContext, ex.taskStatus());
        } catch (Exception ex) {
            statusStageService.failTask(task, runContext, ex);
        }
    }

    /**
     * 处理当前Iso。
     * @return 处理结果
     */
    private String nowIso() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }

    /**
     * 处理put执行Context。
     * @param task 要处理的任务对象
     * @param key key值
     * @param value 待处理的值
     */
    private void putExecutionContext(TaskRecord task, String key, Object value) {
        if (task.executionContext() == null) {
            task.setExecutionContext(new LinkedHashMap<>());
        }
        if (value == null) {
            task.executionContext().remove(key);
            return;
        }
        String normalized = value instanceof String str ? str.trim() : null;
        if (normalized != null && normalized.isEmpty()) {
            task.executionContext().remove(key);
            return;
        }
        task.executionContext().put(key, value);
    }

    /**
     * 处理结果Map。
     * @param run 运行值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> resultMap(Map<String, Object> run) {
        Object result = run.get("result");
        if (result instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    /**
     * 映射值。
     * @param value 待处理的值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    /**
     * 处理string值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    /**
     * 处理int值。
     * @param value 待处理的值
     * @param defaultValue 默认值
     * @return 处理结果
     */
    private int intValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value).trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return defaultValue;
    }

    /**
     * 处理existing视频片段Indices。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private List<Integer> existingVideoClipIndices(TaskRecord task) {
        List<Integer> indices = new ArrayList<>();
        for (Map<String, Object> output : task.outputsView()) {
            if (!TaskResultTypes.isPrimaryVideo(output.get("resultType"))) {
                continue;
            }
            int clipIndex = intValue(output.get("clipIndex"), 0);
            if (clipIndex > 0) {
                indices.add(clipIndex);
            }
        }
        indices.sort(Integer::compareTo);
        return indices;
    }

    /**
     * 处理lastContiguousCompleted片段索引。
     * @param clipIndices 片段Indices值
     * @return 处理结果
     */
    private int lastContiguousCompletedClipIndex(List<Integer> clipIndices) {
        int expected = 1;
        for (Integer clipIndex : clipIndices) {
            if (clipIndex == null) {
                continue;
            }
            if (clipIndex != expected) {
                break;
            }
            expected += 1;
        }
        return expected - 1;
    }

    /**
     * 处理解析ResumeLastFrameURL。
     * @param task 要处理的任务对象
     * @param completedClipCount completed片段数量值
     * @return 处理结果
     */
    private String resolveResumeLastFrameUrl(TaskRecord task, int completedClipCount) {
        String stored = stringValue(task.executionContext().get("lastFrameUrl"));
        if (!stored.isBlank()) {
            return stored;
        }
        if (completedClipCount <= 0) {
            return "";
        }
        for (Map<String, Object> output : task.outputsView()) {
            if (!TaskResultTypes.isPrimaryVideo(output.get("resultType"))) {
                continue;
            }
            if (intValue(output.get("clipIndex"), 0) != completedClipCount) {
                continue;
            }
            Map<String, Object> extra = mapValue(output.get("extra"));
            return firstNonBlank(stringValue(extra.get("lastFrameUrl")), stringValue(extra.get("firstFrameUrl")));
        }
        return "";
    }

    /**
     * 处理首个非空白。
     * @param values 值
     * @return 处理结果
     */
    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }
}
