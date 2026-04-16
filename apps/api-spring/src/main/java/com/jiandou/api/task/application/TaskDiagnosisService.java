package com.jiandou.api.task.application;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.TaskResultTypes;
import com.jiandou.api.task.domain.TaskStatus;
import com.jiandou.api.task.view.TaskViewMapper;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/**
 * 汇总任务执行态、分镜连续性和产物完整性信息，输出诊断结果。
 */
@Service
public class TaskDiagnosisService {

    private final TaskViewMapper taskViewMapper;

    /**
     * 创建新的任务诊断服务。
     * @param taskViewMapper 任务视图映射器值
     */
    public TaskDiagnosisService(TaskViewMapper taskViewMapper) {
        this.taskViewMapper = taskViewMapper;
    }

    /**
     * 处理diagnose。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public Map<String, Object> diagnose(TaskRecord task) {
        Map<String, Object> detail = taskViewMapper.toDetail(task);
        Map<String, Object> monitoring = mapValue(detail.get("monitoring"));
        List<Integer> renderedClipIndices = existingVideoClipIndices(task);
        int plannedClipCount = intValue(monitoring.get("plannedClipCount"), 0);
        int contiguousRenderedClipCount = intValue(monitoring.get("contiguousRenderedClipCount"), 0);
        int latestRenderedClipIndex = intValue(monitoring.get("latestRenderedClipIndex"), 0);
        List<Integer> missingClipIndices = missingClipIndices(plannedClipCount, renderedClipIndices);
        Map<String, Object> latestJoinOutput = latestOutputOfKind(task, TaskResultTypes.VIDEO_JOIN);
        Map<String, Object> latestVideoOutput = latestOutputOfKind(task, TaskResultTypes.VIDEO);
        Map<String, Object> latestVideoExtra = mapValue(latestVideoOutput.get("extra"));
        int joinCount = (int) task.outputsView().stream()
            .filter(item -> TaskResultTypes.isJoin(item.get("resultType")))
            .count();
        int videoClipCount = renderedClipIndices.size();
        boolean hasAudioClip = task.outputsView().stream()
            .filter(item -> TaskResultTypes.isPrimaryVideo(item.get("resultType")))
            .anyMatch(item -> boolValue(mapValue(item.get("extra")).get("hasAudio")));

        List<TaskFinding> findings = new ArrayList<>();
        if (TaskStatus.FAILED.matches(task.status())) {
            findings.add(new TaskFinding(
                "task_failed",
                "high",
                "任务处于失败状态",
                firstNonBlank(task.errorMessage(), "请检查最近一条 trace 和模型调用记录。")
            ));
        }
        if (TaskStatus.PENDING.matches(task.status()) && !task.isQueued()) {
            findings.add(new TaskFinding(
                "pending_not_queued",
                "high",
                "任务状态为 PENDING 但未在队列中",
                "这通常说明 attempt/queue 状态不同步，需要重新入队或重试。"
            ));
        }
        if (plannedClipCount > 0 && contiguousRenderedClipCount < plannedClipCount) {
            findings.add(new TaskFinding(
                "missing_clips",
                contiguousSeverity(task.status()),
                "分镜输出未完整覆盖计划镜头",
                "已连续完成 " + contiguousRenderedClipCount + " / " + plannedClipCount + "，缺失镜头: " + missingClipIndices
            ));
        }
        if (videoClipCount > 1 && joinCount == 0) {
            findings.add(new TaskFinding(
                "join_missing",
                "medium",
                "多镜头任务尚未产出拼接结果",
                "已有 " + videoClipCount + " 段片段，但没有 join 输出。"
            ));
        }
        if (videoClipCount > 0 && !hasAudioClip) {
            findings.add(new TaskFinding(
                "audio_missing",
                "medium",
                "视频片段未检测到音轨",
                "请检查远端视频模型返回以及 generateAudio 参数。"
            ));
        }
        if (TaskStatus.COMPLETED.matches(task.status()) && plannedClipCount > 0 && videoClipCount < plannedClipCount) {
            findings.add(new TaskFinding(
                "completed_but_incomplete",
                "high",
                "任务标记完成但镜头未完整生成",
                "COMPLETED 状态与片段产物数量不一致。"
            ));
        }
        if (findings.isEmpty()) {
            findings.add(new TaskFinding(
                "healthy",
                "info",
                "当前未发现明显阻塞",
                "任务状态、队列与分镜产物看起来基本一致。"
            ));
        }

        String recommendedAction = recommendedAction(task, findings, contiguousRenderedClipCount, plannedClipCount);
        Map<String, Object> recovery = new LinkedHashMap<>();
        recovery.put("canRetry", !TaskStatus.RENDERING.matches(task.status()) && !TaskStatus.ANALYZING.matches(task.status()) && !TaskStatus.PLANNING.matches(task.status()));
        recovery.put("recommendedAction", recommendedAction);
        recovery.put("resumeFromStage", monitoring.get("resumeFromStage"));
        recovery.put("resumeFromClipIndex", intValue(monitoring.get("resumeFromClipIndex"), Math.max(1, contiguousRenderedClipCount + 1)));

        Map<String, Object> continuity = new LinkedHashMap<>();
        continuity.put("plannedClipCount", plannedClipCount);
        continuity.put("renderedClipIndices", renderedClipIndices);
        continuity.put("contiguousRenderedClipCount", contiguousRenderedClipCount);
        continuity.put("missingClipIndices", missingClipIndices);
        continuity.put("latestRenderedClipIndex", latestRenderedClipIndex);
        continuity.put("latestJoinName", stringValue(monitoring.get("latestJoinName")));
        continuity.put("latestJoinClipIndex", intValue(monitoring.get("latestJoinClipIndex"), intValue(latestJoinOutput.get("clipIndex"), 0)));
        continuity.put("latestJoinClipIndices", listValue(monitoring.get("latestJoinClipIndices")));

        Map<String, Object> outputs = new LinkedHashMap<>();
        outputs.put("videoClipCount", videoClipCount);
        outputs.put("joinCount", joinCount);
        outputs.put("latestVideoOutputUrl", firstNonBlank(stringValue(monitoring.get("latestVideoOutputUrl")), stringValue(latestVideoOutput.get("downloadUrl"))));
        outputs.put("latestJoinOutputUrl", firstNonBlank(stringValue(monitoring.get("latestJoinOutputUrl")), stringValue(latestJoinOutput.get("downloadUrl"))));
        outputs.put("latestLastFrameUrl", stringValue(latestVideoExtra.get("lastFrameUrl")));
        outputs.put("hasAudioClip", hasAudioClip);

        Map<String, Object> queue = new LinkedHashMap<>();
        queue.put("isQueued", task.isQueued());
        queue.put("queuePosition", task.queuePosition());
        queue.put("activeAttemptStatus", monitoring.get("activeAttemptStatus"));
        queue.put("activeWorkerInstanceId", monitoring.get("activeWorkerInstanceId"));

        Map<String, Object> diagnosis = new LinkedHashMap<>();
        diagnosis.put("taskId", task.id());
        diagnosis.put("title", task.title());
        diagnosis.put("status", task.status());
        diagnosis.put("severity", highestSeverity(findings));
        diagnosis.put("summary", diagnosisSummary(findings, plannedClipCount, videoClipCount, joinCount));
        diagnosis.put("findings", findings.stream().map(TaskFinding::toMap).toList());
        diagnosis.put("recovery", recovery);
        diagnosis.put("continuity", continuity);
        diagnosis.put("outputs", outputs);
        diagnosis.put("queue", queue);
        return diagnosis;
    }

    /**
     * 处理latest输出类型。
     * @param task 要处理的任务对象
     * @param resultType 结果类型值
     * @return 处理结果
     */
    private Map<String, Object> latestOutputOfKind(TaskRecord task, String resultType) {
        List<Map<String, Object>> outputs = task.outputsView().stream()
            .filter(item -> resultType.equalsIgnoreCase(stringValue(item.get("resultType"))))
            .sorted(Comparator.comparingInt(item -> intValue(item.get("clipIndex"), 0)))
            .toList();
        return outputs.isEmpty() ? Map.of() : outputs.get(outputs.size() - 1);
    }

    /**
     * 处理missing片段Indices。
     * @param plannedClipCount 计划片段数量值
     * @param renderedClipIndices 已渲染片段Indices值
     * @return 处理结果
     */
    private List<Integer> missingClipIndices(int plannedClipCount, List<Integer> renderedClipIndices) {
        if (plannedClipCount <= 0) {
            return List.of();
        }
        LinkedHashSet<Integer> rendered = new LinkedHashSet<>(renderedClipIndices);
        List<Integer> missing = new ArrayList<>();
        for (int index = 1; index <= plannedClipCount; index++) {
            if (!rendered.contains(index)) {
                missing.add(index);
            }
        }
        return missing;
    }

    /**
     * 处理highestSeverity。
     * @param findings findings值
     * @return 处理结果
     */
    private String highestSeverity(List<TaskFinding> findings) {
        int level = 0;
        String label = "info";
        for (TaskFinding finding : findings) {
            int current = switch (finding.severity()) {
                case "high" -> 3;
                case "medium" -> 2;
                case "low" -> 1;
                default -> 0;
            };
            if (current > level) {
                level = current;
                label = finding.severity().isBlank() ? "info" : finding.severity();
            }
        }
        return label;
    }

    /**
     * 处理诊断摘要。
     * @param findings findings值
     * @param plannedClipCount 计划片段数量值
     * @param videoClipCount 视频片段数量值
     * @param joinCount 拼接数量值
     * @return 处理结果
     */
    private String diagnosisSummary(List<TaskFinding> findings, int plannedClipCount, int videoClipCount, int joinCount) {
        String highest = highestSeverity(findings);
        if ("high".equals(highest)) {
            return "任务存在高优先级异常，建议优先查看失败原因与恢复起点。";
        }
        if ("medium".equals(highest)) {
            return "任务主链已跑通，但存在产物完整性或拼接一致性风险。";
        }
        return "任务当前整体健康。计划镜头 " + plannedClipCount + "，视频片段 " + videoClipCount + "，拼接结果 " + joinCount + "。";
    }

    /**
     * 处理recommendedAction。
     * @param task 要处理的任务对象
     * @param findings findings值
     * @param contiguousRenderedClipCount contiguous已渲染片段数量值
     * @param plannedClipCount 计划片段数量值
     * @return 处理结果
     */
    private String recommendedAction(TaskRecord task, List<TaskFinding> findings, int contiguousRenderedClipCount, int plannedClipCount) {
        if (TaskStatus.FAILED.matches(task.status())) {
            return contiguousRenderedClipCount > 0 ? "执行 retry，按已有分镜从失败镜头继续恢复。" : "执行 retry，重新从分析阶段开始。";
        }
        if (TaskStatus.PAUSED.matches(task.status())) {
            return "执行 continue，保持当前分镜进度继续生成。";
        }
        if (plannedClipCount > 1 && findings.stream().anyMatch(item -> "join_missing".equals(item.code()))) {
            return "检查 join worker trace，确认片段已连续落盘后重新触发 join。";
        }
        if (TaskStatus.PENDING.matches(task.status()) && !task.isQueued()) {
            return "重新 enqueue 当前任务，必要时直接 retry 创建新的 attempt。";
        }
        return "继续观察最新 trace 与 stage run，如长时间无进展再执行 retry。";
    }

    /**
     * 处理contiguousSeverity。
     * @param taskStatus 任务状态值
     * @return 处理结果
     */
    private String contiguousSeverity(String taskStatus) {
        return TaskStatus.isTerminal(taskStatus) ? "high" : "medium";
    }

    /**
     * 处理existing视频片段Indices。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    private List<Integer> existingVideoClipIndices(TaskRecord task) {
        LinkedHashSet<Integer> indices = new LinkedHashSet<>();
        for (Map<String, Object> output : task.outputsView()) {
            if (!TaskResultTypes.isPrimaryVideo(output.getOrDefault("resultType", ""))) {
                continue;
            }
            Integer clipIndex = integerValue(output.get("clipIndex"));
            if (clipIndex != null && clipIndex > 0) {
                indices.add(clipIndex);
            }
        }
        return indices.stream().sorted().toList();
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
     * 列出值。
     * @param value 待处理的值
     * @return 处理结果
     */
    @SuppressWarnings("unchecked")
    private List<Object> listValue(Object value) {
        if (value instanceof List<?> list) {
            return (List<Object>) list;
        }
        return List.of();
    }

    /**
     * 处理integer值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private Integer integerValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value == null) {
            return null;
        }
        try {
            return Integer.parseInt(String.valueOf(value).trim());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    /**
     * 处理int值。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private int intValue(Object value, int fallback) {
        Integer resolved = integerValue(value);
        return resolved == null ? fallback : resolved;
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
     * 检查是否布尔值。
     * @param value 待处理的值
     * @return 是否满足条件
     */
    private boolean boolValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        return "true".equalsIgnoreCase(stringValue(value));
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

    /**
     * 诊断项内部先使用强类型记录，只有在接口出参阶段再转成 Map。
     */
    private record TaskFinding(String code, String severity, String title, String detail) {

        /**
         * 处理转为Map。
         * @return 处理结果
         */
        Map<String, Object> toMap() {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("code", code);
            row.put("severity", severity);
            row.put("title", title);
            row.put("detail", detail);
            return row;
        }
    }
}
