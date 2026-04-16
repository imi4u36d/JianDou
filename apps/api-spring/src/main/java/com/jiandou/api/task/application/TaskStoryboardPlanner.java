package com.jiandou.api.task.application;

import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.task.TaskRecord;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Service;

/**
 * 封装分镜脚本解析、镜头提示词生成和时长规划逻辑，降低 worker 状态机体积。
 */
@Service
public class TaskStoryboardPlanner {
    private static final int CLIP_MIN_SECONDS = 5;
    private static final int CLIP_MAX_SECONDS = 12;

    private static final Pattern SCRIPT_DURATION_RANGE_PATTERN = Pattern.compile(
        "(?<left>\\d{1,3}(?:\\.\\d+)?)\\s*(?:-|~|～|—|到)\\s*(?<right>\\d{1,3}(?:\\.\\d+)?)\\s*(?:s|sec|secs|second|seconds|秒)",
        Pattern.CASE_INSENSITIVE
    );
    private static final Pattern SCRIPT_DURATION_VALUE_PATTERN = Pattern.compile(
        "(?<![\\d.])(?<value>\\d{1,3}(?:\\.\\d+)?)\\s*(?:s|sec|secs|second|seconds|秒)(?![a-zA-Z])",
        Pattern.CASE_INSENSITIVE
    );
    private static final Pattern PLAIN_DURATION_RANGE_PATTERN = Pattern.compile(
        "^\\s*(?<left>\\d{1,3}(?:\\.\\d+)?)\\s*(?:-|~|～|—|到)\\s*(?<right>\\d{1,3}(?:\\.\\d+)?)\\s*$",
        Pattern.CASE_INSENSITIVE
    );
    private static final Pattern PLAIN_DURATION_VALUE_PATTERN = Pattern.compile(
        "^\\s*(?<value>\\d{1,3}(?:\\.\\d+)?)\\s*$",
        Pattern.CASE_INSENSITIVE
    );

    private final ModelRuntimePropertiesResolver modelResolver;

    /**
     * 创建新的任务分镜规划器。
     * @param modelResolver 模型解析器值
     */
    public TaskStoryboardPlanner(ModelRuntimePropertiesResolver modelResolver) {
        this.modelResolver = modelResolver;
    }

    /**
     * 构建Sequential片段Prompts。
     * @param task 要处理的任务对象
     * @param storyboardMarkdown 分镜Markdown值
     * @return 处理结果
     */
    public List<String> buildSequentialClipPrompts(TaskRecord task, String storyboardMarkdown) {
        return buildStoryboardShotPlans(task, storyboardMarkdown).stream().map(StoryboardShotPlan::videoPrompt).toList();
    }

    /**
     * 构建分镜ShotPlans。
     * @param task 要处理的任务对象
     * @param storyboardMarkdown 分镜Markdown值
     * @return 处理结果
     */
    public List<StoryboardShotPlan> buildStoryboardShotPlans(TaskRecord task, String storyboardMarkdown) {
        List<StoryboardShotPlan> shotPlans = extractStoryboardShotPlans(storyboardMarkdown);
        if (!shotPlans.isEmpty()) {
            return shotPlans;
        }
        throw new IllegalStateException("分镜解析失败，未识别到有效镜头。");
    }

    /**
     * 构建分镜视频Prompts。
     * @param storyboardMarkdown 分镜Markdown值
     * @return 处理结果
     */
    public List<String> buildStoryboardVideoPrompts(String storyboardMarkdown) {
        List<StoryboardShotPlan> shotPlans = extractStoryboardShotPlans(storyboardMarkdown);
        if (shotPlans.isEmpty()) {
            throw new IllegalStateException("分镜解析失败，未识别到有效镜头。");
        }
        return shotPlans.stream().map(StoryboardShotPlan::videoPrompt).toList();
    }

    /**
     * 处理解析Requested输出数量。
     * @param task 要处理的任务对象
     * @param storyboardClipCount 分镜片段数量值
     * @return 处理结果
     */
    public int resolveRequestedOutputCount(TaskRecord task, int storyboardClipCount) {
        int availableClipCount = Math.max(1, storyboardClipCount);
        if (task.requestSnapshot() == null || task.requestSnapshot().outputCount().auto()) {
            return availableClipCount;
        }
        Integer requested = task.requestSnapshot().outputCount().count();
        if (requested == null) {
            return availableClipCount;
        }
        return Math.max(1, Math.min(requested, availableClipCount));
    }

    /**
     * 处理请求快照输出数量。
     * @param task 要处理的任务对象
     * @return 处理结果
     */
    public Object requestSnapshotOutputCount(TaskRecord task) {
        if (task.requestSnapshot() == null) {
            return "auto";
        }
        return task.requestSnapshot().outputCount().toValue();
    }

    /**
     * 构建片段时长规划Context。
     * @param clipDurationPlan 片段时长规划值
     * @param storyboardDurationRanges 分镜时长Ranges值
     * @return 处理结果
     */
    public List<Map<String, Object>> buildClipDurationPlanContext(List<int[]> clipDurationPlan, List<int[]> storyboardDurationRanges) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (int index = 0; index < clipDurationPlan.size(); index++) {
            int[] plan = clipDurationPlan.get(index);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("clipIndex", index + 1);
            row.put("targetDurationSeconds", plan[0]);
            row.put("minDurationSeconds", plan[1]);
            row.put("maxDurationSeconds", plan[2]);
            if (index < storyboardDurationRanges.size()) {
                int[] scripted = storyboardDurationRanges.get(index);
                row.put("durationSource", "storyboard");
                row.put("scriptMinDurationSeconds", scripted[0]);
                row.put("scriptMaxDurationSeconds", scripted[1]);
            } else {
                row.put("durationSource", "task_average");
            }
            rows.add(row);
        }
        return rows;
    }

    /**
     * 构建片段时长规划。
     * @param task 要处理的任务对象
     * @param defaultDurationSeconds 默认时长Seconds值
     * @param clipCount 片段数量值
     * @param storyboardMarkdown 分镜Markdown值
     * @return 处理结果
     */
    public List<int[]> buildClipDurationPlan(TaskRecord task, int defaultDurationSeconds, int clipCount, String storyboardMarkdown) {
        int normalizedClipCount = Math.max(1, clipCount);
        int totalMin = Math.max(1, task.minDurationSeconds() > 0 ? task.minDurationSeconds() : defaultDurationSeconds);
        int totalMax = Math.max(totalMin, task.maxDurationSeconds() > 0 ? task.maxDurationSeconds() : defaultDurationSeconds);
        List<int[]> ranges = extractStoryboardShotDurationRanges(storyboardMarkdown);
        int scriptedClipCount = Math.min(ranges.size(), normalizedClipCount);
        int scriptedMinSum = 0;
        int scriptedMaxSum = 0;
        for (int index = 0; index < scriptedClipCount; index++) {
            int[] range = ranges.get(index);
            scriptedMinSum += Math.max(1, range[0]);
            scriptedMaxSum += Math.max(Math.max(1, range[0]), range[1]);
        }
        int unresolvedClipCount = Math.max(0, normalizedClipCount - scriptedClipCount);
        int globalMin = unresolvedClipCount == 0
            ? CLIP_MIN_SECONDS
            : Math.max(1, Math.round((float) Math.max(unresolvedClipCount, totalMin - scriptedMinSum) / unresolvedClipCount));
        int globalMax = unresolvedClipCount == 0
            ? globalMin
            : Math.max(globalMin, Math.round((float) Math.max(unresolvedClipCount, totalMax - scriptedMaxSum) / unresolvedClipCount));
        globalMin = clamp(globalMin, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS);
        globalMax = clamp(globalMax, globalMin, CLIP_MAX_SECONDS);
        List<int[]> plan = new ArrayList<>();
        for (int index = 0; index < normalizedClipCount; index++) {
            boolean scripted = index < ranges.size();
            int clipMin = scripted ? ranges.get(index)[0] : globalMin;
            int clipMax = scripted ? Math.max(clipMin, ranges.get(index)[1]) : globalMax;
            clipMin = clamp(clipMin, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS);
            clipMax = clamp(clipMax, clipMin, CLIP_MAX_SECONDS);
            int clipTarget = scripted
                ? clipMin
                : Math.max(clipMin, Math.min(clipMax, Math.round((clipMin + clipMax) / 2.0f)));
            clipTarget = clamp(clipTarget, clipMin, clipMax);
            plan.add(new int[] {clipTarget, clipMin, clipMax});
        }
        return plan;
    }

    /**
     * 规范化片段时长规划。
     * @param requestedVideoModel requested视频模型值
     * @param clipDurationPlan 片段时长规划值
     * @return 处理结果
     */
    public List<int[]> normalizeClipDurationPlan(String requestedVideoModel, List<int[]> clipDurationPlan) {
        if (clipDurationPlan == null || clipDurationPlan.isEmpty()) {
            return List.of();
        }
        List<Integer> supportedDurations = supportedVideoDurations(requestedVideoModel);
        if (supportedDurations.isEmpty()) {
            return clipDurationPlan;
        }
        List<int[]> normalizedPlan = new ArrayList<>(clipDurationPlan.size());
        for (int[] planItem : clipDurationPlan) {
            if (planItem == null || planItem.length < 3) {
                continue;
            }
            normalizedPlan.add(normalizeClipDurationRange(supportedDurations, planItem[0], planItem[1], planItem[2]));
        }
        return normalizedPlan;
    }

    /**
     * 处理extract分镜Shot时长Ranges。
     * @param storyboardMarkdown 分镜Markdown值
     * @return 处理结果
     */
    public List<int[]> extractStoryboardShotDurationRanges(String storyboardMarkdown) {
        String normalized = stringValue(storyboardMarkdown);
        if (normalized.isBlank()) {
            return List.of();
        }
        List<String> lines = List.of(normalized.split("\\R"));
        StoryboardTableSchema schema = detectStoryboardTableSchema(lines);
        List<int[]> ranges = new ArrayList<>();
        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            if (!stripped.startsWith("|")) {
                continue;
            }
            List<String> cells = splitTableRow(stripped);
            if (cells.size() < 2 || isDividerRow(cells) || schema.isHeaderRow(cells)) {
                continue;
            }
            String first = schema.cell(cells, schema.shotNoIndex(), 0);
            if (first.isBlank() || first.contains("镜号") || first.toLowerCase().contains("shot")) {
                continue;
            }
            int legacyDurationFallbackIndex = schema.headerCells().isEmpty() ? cells.size() - 1 : -1;
            String durationCell = schema.cell(cells, schema.durationIndex(), legacyDurationFallbackIndex);
            int[] parsed = parseDurationRangeHint(durationCell);
            if (parsed != null) {
                ranges.add(parsed);
            }
        }
        if (!ranges.isEmpty()) {
            return ranges;
        }
        Matcher matcher = SCRIPT_DURATION_RANGE_PATTERN.matcher(normalized);
        while (matcher.find()) {
            int[] parsed = parseDurationRangeHint(matcher.group());
            if (parsed != null) {
                ranges.add(parsed);
            }
        }
        return ranges;
    }

    /**
     * 处理extract分镜ShotPlans。
     * @param storyboardMarkdown 分镜Markdown值
     * @return 处理结果
     */
    private List<StoryboardShotPlan> extractStoryboardShotPlans(String storyboardMarkdown) {
        String normalized = stringValue(storyboardMarkdown);
        if (normalized.isBlank()) {
            return List.of();
        }
        List<String> lines = List.of(normalized.split("\\R"));
        StoryboardTableSchema schema = detectStoryboardTableSchema(lines);
        List<StoryboardShotPlan> shotPlans = new ArrayList<>();

        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            if (!stripped.startsWith("|")) {
                continue;
            }
            List<String> cells = splitTableRow(stripped);
            if (cells.size() < 2 || isDividerRow(cells) || schema.isHeaderRow(cells)) {
                continue;
            }
            String first = schema.cell(cells, schema.shotNoIndex(), 0);
            if (first.isBlank() || first.contains("镜号") || first.toLowerCase().contains("shot")) {
                continue;
            }
            String shotIndex = first.replaceAll("[^0-9一二三四五六七八九十百千两]", "");
            if (shotIndex.isBlank()) {
                shotIndex = String.valueOf(shotPlans.size() + 1);
            }
            int sequentialIndex = shotPlans.size() + 1;
            int legacyCameraFallbackIndex = schema.headerCells().isEmpty() ? 2 : -1;
            int legacyDurationFallbackIndex = schema.headerCells().isEmpty() ? cells.size() - 1 : -1;
            String scene = schema.cell(cells, schema.sceneIndex(), 1);
            String time = schema.cell(cells, schema.timeIndex(), -1);
            String shotSpec = normalizeStoryboardPromptValue(schema.cell(cells, schema.shotSpecIndex(), legacyCameraFallbackIndex));
            String movement = normalizeStoryboardPromptValue(schema.cell(cells, schema.movementIndex(), legacyCameraFallbackIndex));
            String cameraMovement = firstNonBlank(
                normalizeStoryboardPromptValue(schema.cell(cells, schema.cameraMovementIndex(), -1)),
                movement
            );
            String explicitMotion = normalizeStoryboardPromptValue(schema.cell(cells, schema.motionIndex(), -1));
            String explicitFirstFrame = normalizeStoryboardPromptValue(schema.cell(cells, schema.firstFramePromptIndex(), -1));
            String explicitLastFrame = normalizeStoryboardPromptValue(schema.cell(cells, schema.lastFramePromptIndex(), -1));
            String visual = schema.cell(cells, schema.visualIndex(), 3);
            String dynamic = schema.cell(cells, schema.dynamicIndex(), -1);
            String storyDescription = schema.cell(cells, schema.storyDescriptionIndex(), -1);
            String characterAppearance = schema.cell(cells, schema.characterAppearanceIndex(), -1);
            String action = schema.cell(cells, schema.actionIndex(), -1);
            String emotion = schema.cell(cells, schema.emotionIndex(), -1);
            String dialogue = normalizeStoryboardPromptValue(schema.cell(cells, schema.dialogueIndex(), -1));
            String audio = normalizeStoryboardPromptValue(schema.cell(cells, schema.audioIndex(), -1));
            String durationHint = schema.cell(cells, schema.durationIndex(), legacyDurationFallbackIndex);
            String firstFramePrompt = explicitFirstFrame;
            String lastFramePrompt = explicitLastFrame;
            String motion = explicitMotion;
            if (motion.isBlank()) {
                motion = normalizeStoryboardPromptValue(action);
            }
            cameraMovement = firstNonBlank(extractCameraMovement(cameraMovement), normalizeStoryboardPromptValue(cameraMovement));
            if (cameraMovement.isBlank()) {
                cameraMovement = inferCameraMovement(shotSpec, motion);
            }
            if (cameraMovement.isBlank()) {
                cameraMovement = "static";
            }
            String sceneDescription = normalizeStoryboardPromptValue(storyDescription);
            if (sceneDescription.isBlank()) {
                continue;
            }
            if (firstFramePrompt.isBlank()) {
                firstFramePrompt = sceneDescription;
            }
            if (lastFramePrompt.isBlank()) {
                lastFramePrompt = sceneDescription;
            }
            String imagePrompt = sequentialIndex == 1 ? firstNonBlank(firstFramePrompt, sceneDescription) : "";
            String videoPromptBase = firstNonBlank(lastFramePrompt, sceneDescription);
            String videoPrompt = buildContinuousClipPrompt(videoPromptBase, motion, cameraMovement, "", audio);
            if (!videoPrompt.isBlank()) {
                shotPlans.add(new StoryboardShotPlan(
                    sequentialIndex,
                    shotIndex,
                    scene,
                    firstFramePrompt,
                    lastFramePrompt,
                    motion,
                    cameraMovement,
                    durationHint,
                    imagePrompt,
                    videoPrompt
                ));
            }
        }
        if (!shotPlans.isEmpty()) {
            return shotPlans;
        }
        return List.of();
    }

    /**
     * 规范化片段时长范围。
     * @param supportedDurations supportedDurations值
     * @param targetDurationSeconds target时长Seconds值
     * @param minDurationSeconds 最小时长Seconds值
     * @param maxDurationSeconds 最大时长Seconds值
     * @return 处理结果
     */
    private int[] normalizeClipDurationRange(
        List<Integer> supportedDurations,
        int targetDurationSeconds,
        int minDurationSeconds,
        int maxDurationSeconds
    ) {
        int normalizedTarget = clamp(targetDurationSeconds, CLIP_MIN_SECONDS, CLIP_MAX_SECONDS);
        int normalizedMin = clamp(Math.min(minDurationSeconds, maxDurationSeconds), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS);
        int normalizedMax = clamp(Math.max(minDurationSeconds, maxDurationSeconds), normalizedMin, CLIP_MAX_SECONDS);
        List<Integer> inRange = supportedDurations.stream()
            .filter(candidate -> candidate >= normalizedMin && candidate <= normalizedMax)
            .toList();
        if (!inRange.isEmpty()) {
            return new int[] {
                closestSupportedDuration(inRange, normalizedTarget),
                inRange.get(0),
                inRange.get(inRange.size() - 1)
            };
        }
        int resolved = closestSupportedDuration(supportedDurations, normalizedTarget);
        return new int[] {resolved, resolved, resolved};
    }

    /**
     * 处理supported视频Durations。
     * @param requestedVideoModel requested视频模型值
     * @return 处理结果
     */
    private List<Integer> supportedVideoDurations(String requestedVideoModel) {
        String normalizedModel = stringValue(requestedVideoModel);
        if (normalizedModel.isBlank()) {
            return List.of();
        }
        Map<String, String> section = modelResolver.section("model.models.\"" + normalizedModel + "\"");
        String raw = stringValue(section.get("supported_durations"));
        if (raw.isBlank()) {
            return List.of();
        }
        List<Integer> values = new ArrayList<>();
        for (String token : raw.split(",")) {
            try {
                int value = Integer.parseInt(token.trim());
                if (value > 0 && !values.contains(value)) {
                    values.add(value);
                }
            } catch (NumberFormatException ignored) {
            }
        }
        values.sort(Integer::compareTo);
        return values;
    }

    /**
     * 处理closestSupported时长。
     * @param candidates candidates值
     * @param requestedDurationSeconds requested时长Seconds值
     * @return 处理结果
     */
    private int closestSupportedDuration(List<Integer> candidates, int requestedDurationSeconds) {
        int resolved = candidates.get(0);
        int smallestDistance = Math.abs(resolved - requestedDurationSeconds);
        for (int candidate : candidates) {
            int distance = Math.abs(candidate - requestedDurationSeconds);
            if (distance < smallestDistance || (distance == smallestDistance && candidate > resolved)) {
                resolved = candidate;
                smallestDistance = distance;
            }
        }
        return resolved;
    }

    /**
     * 解析时长范围提示。
     * @param text 文本值
     * @return 处理结果
     */
    private int[] parseDurationRangeHint(String text) {
        String normalized = stringValue(text);
        if (normalized.isBlank()) {
            return null;
        }
        Matcher rangeMatcher = SCRIPT_DURATION_RANGE_PATTERN.matcher(normalized);
        if (rangeMatcher.find()) {
            int left = safeRoundedSeconds(rangeMatcher.group("left"));
            int right = safeRoundedSeconds(rangeMatcher.group("right"));
            int low = clamp(Math.min(left, right), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS);
            int high = clamp(Math.max(left, right), low, CLIP_MAX_SECONDS);
            return new int[] {low, high};
        }
        Matcher valueMatcher = SCRIPT_DURATION_VALUE_PATTERN.matcher(normalized);
        if (valueMatcher.find()) {
            int value = clamp(safeRoundedSeconds(valueMatcher.group("value")), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS);
            return new int[] {value, value};
        }
        Matcher plainRangeMatcher = PLAIN_DURATION_RANGE_PATTERN.matcher(normalized);
        if (plainRangeMatcher.find()) {
            int left = safeRoundedSeconds(plainRangeMatcher.group("left"));
            int right = safeRoundedSeconds(plainRangeMatcher.group("right"));
            int low = clamp(Math.min(left, right), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS);
            int high = clamp(Math.max(left, right), low, CLIP_MAX_SECONDS);
            return new int[] {low, high};
        }
        Matcher plainValueMatcher = PLAIN_DURATION_VALUE_PATTERN.matcher(normalized);
        if (plainValueMatcher.find()) {
            int value = clamp(safeRoundedSeconds(plainValueMatcher.group("value")), CLIP_MIN_SECONDS, CLIP_MAX_SECONDS);
            return new int[] {value, value};
        }
        return null;
    }

    /**
     * 处理safeRoundedSeconds。
     * @param value 待处理的值
     * @return 处理结果
     */
    private int safeRoundedSeconds(String value) {
        try {
            return Math.max(1, Math.min(120, (int) Math.round(Double.parseDouble(stringValue(value)))));
        } catch (NumberFormatException ex) {
            return 1;
        }
    }

    /**
     * 处理clamp。
     * @param value 待处理的值
     * @param min 最小值
     * @param max 最大值
     * @return 处理结果
     */
    private int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    /**
     * 处理splitTable行。
     * @param row 行值
     * @return 处理结果
     */
    private List<String> splitTableRow(String row) {
        String trimmed = row.trim();
        if (!trimmed.startsWith("|")) {
            return List.of();
        }
        String[] parts = trimmed.substring(1, trimmed.endsWith("|") ? trimmed.length() - 1 : trimmed.length()).split("\\|");
        List<String> cells = new ArrayList<>();
        for (String part : parts) {
            cells.add(part.trim());
        }
        return cells;
    }

    /**
     * 处理detect分镜TableSchema。
     * @param lines lines值
     * @return 处理结果
     */
    private StoryboardTableSchema detectStoryboardTableSchema(List<String> lines) {
        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            if (!stripped.startsWith("|")) {
                continue;
            }
            List<String> cells = splitTableRow(stripped);
            if (cells.isEmpty() || isDividerRow(cells)) {
                continue;
            }
            if (looksLikeHeaderRow(cells)) {
                return StoryboardTableSchema.fromHeader(cells);
            }
        }
        return StoryboardTableSchema.empty();
    }

    /**
     * 检查是否looksLikeHeader行。
     * @param cells cells值
     * @return 是否满足条件
     */
    private boolean looksLikeHeaderRow(List<String> cells) {
        for (String cell : cells) {
            String normalized = normalizeStoryboardHeader(cell);
            if (normalized.contains("shot") || normalized.contains("镜号") || normalized.contains("景别")
                || normalized.contains("运镜") || normalized.contains("镜头参数") || normalized.contains("画面") || normalized.contains("visual")
                || normalized.contains("audio") || normalized.contains("duration") || normalized.contains("时长")
                || normalized.contains("剧情摘要") || normalized.contains("seedream") || normalized.contains("seedance")
                || normalized.contains("剧情描述") || normalized.contains("画面叙述") || normalized.contains("storydescription")
                || normalized.contains("scene") || normalized.contains("time") || normalized.contains("lighting")
                || normalized.contains("atmosphere") || normalized.contains("appearance") || normalized.contains("action")
                || normalized.contains("emotion") || normalized.contains("camera") || normalized.contains("continuity")) {
                return true;
            }
        }
        return false;
    }

    /**
     * 规范化分镜Header。
     * @param text 文本值
     * @return 处理结果
     */
    private String normalizeStoryboardHeader(String text) {
        return stringValue(text)
            .trim()
            .toLowerCase()
            .replaceAll("[\\s_\\-()（）/\\\\+:：·,.，]", "");
    }

    /**
     * 规范化分镜提示词值。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String normalizeStoryboardPromptValue(String value) {
        return stringValue(value)
            .replace("<br>", " ")
            .replace("<br/>", " ")
            .replace("<br />", " ")
            .replaceAll("\\s+", " ")
            .trim();
    }

    /**
     * 构建Continuous片段提示词。
     * @param lastFramePrompt lastFrame提示词值
     * @param motion motion值
     * @param cameraMovement cameraMovement值
     * @param dialogue dialogue值
     * @param audio audio值
     * @return 处理结果
     */
    private String buildContinuousClipPrompt(String lastFramePrompt, String motion, String cameraMovement, String dialogue, String audio) {
        List<String> parts = new ArrayList<>();
        if (!lastFramePrompt.isBlank()) {
            parts.add(lastFramePrompt);
        }
        if (!motion.isBlank()) {
            parts.add("动作延展：" + motion);
        }
        if (!cameraMovement.isBlank()) {
            parts.add("运镜：" + cameraMovement);
        }
        String dialogueInstruction = dialogueInstruction(dialogue);
        if (!dialogueInstruction.isBlank()) {
            parts.add(dialogueInstruction);
        }
        if (!audio.isBlank()) {
            parts.add("音频设计：" + audio);
        }
        return truncateText(String.join("；", parts), 1400);
    }

    /**
     * 处理dialogueInstruction。
     * @param dialogue dialogue值
     * @return 处理结果
     */
    private String dialogueInstruction(String dialogue) {
        String normalized = normalizeStoryboardPromptValue(dialogue);
        if (normalized.isBlank()) {
            return "";
        }
        String lowered = normalized.toLowerCase();
        if (normalized.startsWith("画外音") || normalized.startsWith("旁白")
            || lowered.startsWith("voice over") || lowered.startsWith("voiceover")
            || lowered.startsWith("off-screen") || lowered.startsWith("offscreen")) {
            return "可听见的画外音：" + normalized + "；说话者可暂不出镜，画外音放在镜头中段，前0.5秒与后0.5秒保持人声留白，仅保留动作或环境声缓冲。";
        }
        if (normalized.startsWith("独白：") || normalized.startsWith("独白:")) {
            return "可听见的人声独白：" + normalized + "；独白放在镜头中段，前0.5秒与后0.5秒保持无人声，仅保留动作或环境声缓冲。";
        }
        if (normalized.contains("“") || normalized.contains("\"") || normalized.contains("：") || normalized.contains(":")) {
            return "可听见的人声对白：" + normalized + "；对白放在镜头中段，前0.5秒与后0.5秒保持无人声，仅保留动作或环境声缓冲。";
        }
        return "可听见的人声独白：独白：" + normalized + "；独白放在镜头中段，前0.5秒与后0.5秒保持无人声，仅保留动作或环境声缓冲。";
    }

    /**
     * 处理inferCameraMovement。
     * @param shotSpec shotSpec值
     * @param motion motion值
     * @return 处理结果
     */
    private String inferCameraMovement(String shotSpec, String motion) {
        String normalizedShotSpec = normalizeStoryboardPromptValue(shotSpec);
        String normalizedMotion = normalizeStoryboardPromptValue(motion);
        for (String candidate : List.of(normalizedShotSpec, normalizedMotion)) {
            String inferred = extractCameraMovement(candidate);
            if (!inferred.isBlank()) {
                return inferred;
            }
        }
        return "";
    }

    /**
     * 处理extractCameraMovement。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String extractCameraMovement(String value) {
        String normalized = normalizeStoryboardPromptValue(value);
        if (normalized.isBlank()) {
            return "";
        }
        for (String token : normalized.split("[/／+＋,，;；|｜]")) {
            String trimmed = token.trim();
            if (looksLikeCameraMovement(trimmed)) {
                return trimmed;
            }
        }
        return looksLikeCameraMovement(normalized) ? normalized : "";
    }

    /**
     * 检查是否looksLikeCameraMovement。
     * @param value 待处理的值
     * @return 是否满足条件
     */
    private boolean looksLikeCameraMovement(String value) {
        String normalized = normalizeStoryboardPromptValue(value).toLowerCase();
        if (normalized.isBlank()) {
            return false;
        }
        return normalized.contains("推")
            || normalized.contains("拉")
            || normalized.contains("摇")
            || normalized.contains("移")
            || normalized.contains("跟")
            || normalized.contains("甩")
            || normalized.contains("升")
            || normalized.contains("降")
            || normalized.contains("环绕")
            || normalized.contains("环拍")
            || normalized.contains("手持")
            || normalized.contains("dolly")
            || normalized.contains("push")
            || normalized.contains("pull")
            || normalized.contains("pan")
            || normalized.contains("tilt")
            || normalized.contains("truck")
            || normalized.contains("track")
            || normalized.contains("orbit")
            || normalized.contains("handheld")
            || normalized.contains("whip");
    }

    /**
     * 处理首个非空白。
     * @param values 值
     * @return 处理结果
     */
    private String firstNonBlank(String... values) {
        for (String value : values) {
            String normalized = stringValue(value);
            if (!normalized.isBlank()) {
                return normalized;
            }
        }
        return "";
    }

    /**
     * 检查是否Divider行。
     * @param cells cells值
     * @return 是否满足条件
     */
    private boolean isDividerRow(List<String> cells) {
        for (String cell : cells) {
            if (!cell.matches("[:\\-\\s]*")) {
                return false;
            }
        }
        return true;
    }

    /**
     * 处理truncate文本。
     * @param value 待处理的值
     * @param maxLength 最大Length值
     * @return 处理结果
     */
    private String truncateText(String value, int maxLength) {
        String normalized = stringValue(value);
        if (normalized.length() <= maxLength) {
            return normalized;
        }
        return normalized.substring(0, Math.max(0, maxLength - 1)).trim() + "…";
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
     * 处理分镜TableSchema。
     * @param headerCells headerCells值
     * @param shotNoIndex shotNo索引值
     * @param sceneIndex scene索引值
     * @param timeIndex 时间索引值
     * @param shotSpecIndex shotSpec索引值
     * @param movementIndex movement索引值
     * @param firstFramePromptIndex 首个Frame提示词索引值
     * @param lastFramePromptIndex lastFrame提示词索引值
     * @param motionIndex motion索引值
     * @param cameraMovementIndex cameraMovement索引值
     * @param visualIndex visual索引值
     * @param dynamicIndex dynamic索引值
     * @param storyDescriptionIndex storyDescription索引值
     * @param characterAppearanceIndex characterAppearance索引值
     * @param actionIndex action索引值
     * @param emotionIndex emotion索引值
     * @param lightingIndex lighting索引值
     * @param atmosphereIndex atmosphere索引值
     * @param dialogueIndex dialogue索引值
     * @param audioIndex audio索引值
     * @param durationIndex 时长索引值
     * @return 处理结果
     */
    private record StoryboardTableSchema(
        List<String> headerCells,
        Integer shotNoIndex,
        Integer sceneIndex,
        Integer timeIndex,
        Integer shotSpecIndex,
        Integer movementIndex,
        Integer firstFramePromptIndex,
        Integer lastFramePromptIndex,
        Integer motionIndex,
        Integer cameraMovementIndex,
        Integer visualIndex,
        Integer dynamicIndex,
        Integer storyDescriptionIndex,
        Integer characterAppearanceIndex,
        Integer actionIndex,
        Integer emotionIndex,
        Integer lightingIndex,
        Integer atmosphereIndex,
        Integer dialogueIndex,
        Integer audioIndex,
        Integer durationIndex
    ) {
        /**
         * 处理empty。
         * @return 处理结果
         */
        static StoryboardTableSchema empty() {
            return new StoryboardTableSchema(
                List.of(),
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null
            );
        }

        /**
         * 处理fromHeader。
         * @param headers headers值
         * @return 处理结果
         */
        static StoryboardTableSchema fromHeader(List<String> headers) {
            return new StoryboardTableSchema(
                List.copyOf(headers),
                resolve(headers, "shotno", "shot", "镜号"),
                resolve(headers, "剧情摘要", "剧情节点", "场景", "scene", "summary"),
                resolve(headers, "time", "时间"),
                resolve(headers, "camerashottype", "camerashot", "shotspec", "景别角度", "景别", "镜头语言", "镜头参数", "shotsize", "angle", "shottype"),
                resolve(headers, "cameramovement", "movement", "运镜"),
                resolve(headers, "firstframeprompt", "firstframe", "首帧提示词", "首帧"),
                resolve(headers, "lastframeprompt", "lastframe", "尾帧提示词", "尾帧"),
                resolve(headers, "motion", "动作"),
                resolve(headers, "cameramovement", "movement", "运镜"),
                resolve(headers, "统一提示词", "统一画面提示词", "镜头提示词", "cinematicvisualdescription", "visualdescription", "visualcontent", "视觉描述", "画面提示词", "画面细节描述", "画面描述", "visualprompt", "seedream提示词", "seedream", "关键帧", "visual"),
                resolve(headers, "统一提示词", "统一画面提示词", "镜头提示词", "seedance提示词", "seedance", "动态与运镜", "动态", "衔接逻辑", "转场", "转场衔接", "镜头节拍", "continuity", "motion"),
                resolve(
                    headers,
                    "剧情描述",
                    "剧情画面描述",
                    "剧情画面与声音描述",
                    "剧情画面与声音长描述",
                    "整段描述",
                    "合并长段描述",
                    "长段描述",
                    "scene description",
                    "story description",
                    "combined description",
                    "merged description",
                    "storyline",
                    "plot description",
                    "story narrative",
                    "画面叙述"
                ),
                resolve(headers, "characterappearance", "appearance", "人物外观", "角色外观"),
                resolve(headers, "action", "动作", "表演调度", "动作节拍", "动作链", "角色动作", "表演", "blocking", "beat", "performance"),
                resolve(headers, "sentiment", "emotion", "情绪", "情感分析", "感情分析", "情感", "感情"),
                resolve(headers, "lighting", "光线"),
                resolve(headers, "atmosphere", "氛围"),
                resolve(headers, "dialogue", "独白", "对话", "对白", "对白人声", "台词", "字幕", "对话独白画外音", "对白独白画外音", "dialoguevoiceover"),
                resolve(headers, "audio", "音效", "bgm", "sfx", "声音与对白", "声音设计转场", "声音设计", "音效转场设计", "转场设计"),
                resolve(headers, "duration", "时长", "秒")
            );
        }

        /**
         * 处理解析。
         * @param headers headers值
         * @param aliases aliases值
         * @return 处理结果
         */
        private static Integer resolve(List<String> headers, String... aliases) {
            for (int index = 0; index < headers.size(); index++) {
                String header = headers.get(index)
                    .trim()
                    .toLowerCase()
                    .replaceAll("[\\s_\\-()（）/\\\\+:：·,.，]", "");
                for (String alias : aliases) {
                    if (header.contains(alias)) {
                        return index;
                    }
                }
            }
            return null;
        }

        /**
         * 检查是否Header行。
         * @param cells cells值
         * @return 是否满足条件
         */
        boolean isHeaderRow(List<String> cells) {
            if (headerCells.isEmpty() || cells.size() != headerCells.size()) {
                return false;
            }
            for (int index = 0; index < cells.size(); index++) {
                String left = cells.get(index).trim();
                String right = headerCells.get(index).trim();
                if (!left.equalsIgnoreCase(right)) {
                    return false;
                }
            }
            return true;
        }

        /**
         * 处理cell。
         * @param cells cells值
         * @param index 索引值
         * @param fallbackIndex 兜底索引值
         * @return 处理结果
         */
        String cell(List<String> cells, Integer index, int fallbackIndex) {
            int resolvedIndex = index != null ? index : fallbackIndex;
            if (resolvedIndex < 0 || resolvedIndex >= cells.size()) {
                return "";
            }
            Object value = cells.get(resolvedIndex);
            return value == null ? "" : String.valueOf(value).trim();
        }
    }

    /**
     * 处理分镜Shot规划。
     * @param sequentialIndex sequential索引值
     * @param shotLabel shot标签值
     * @param scene scene值
     * @param firstFramePrompt 首个Frame提示词值
     * @param lastFramePrompt lastFrame提示词值
     * @param motion motion值
     * @param cameraMovement cameraMovement值
     * @param durationHint 时长提示值
     * @param imagePrompt 图像提示词值
     * @param videoPrompt 视频提示词值
     * @return 处理结果
     */
    public record StoryboardShotPlan(
        int sequentialIndex,
        String shotLabel,
        String scene,
        String firstFramePrompt,
        String lastFramePrompt,
        String motion,
        String cameraMovement,
        String durationHint,
        String imagePrompt,
        String videoPrompt
    ) {
    }
}
