package com.jiandou.api.task;

import com.jiandou.api.generation.ModelRuntimePropertiesResolver;
import com.jiandou.api.task.domain.GenerationRequestSnapshot;
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
    private static final Pattern SHOT_HEADING_PATTERN = Pattern.compile(
        "^\\s*#{2,4}\\s*分镜\\s*(?<index>[0-9一二三四五六七八九十百千两]+)?\\s*[·\\-：:]*\\s*(?<title>.*)$"
    );

    private final ModelRuntimePropertiesResolver modelResolver;

    public TaskStoryboardPlanner(ModelRuntimePropertiesResolver modelResolver) {
        this.modelResolver = modelResolver;
    }

    public List<String> buildSequentialClipPrompts(TaskRecord task, String storyboardMarkdown) {
        List<StoryboardShotPlan> shotPlans = buildStoryboardShotPlans(task, storyboardMarkdown);
        if (shotPlans.isEmpty()) {
            return List.of(buildVisualPrompt(task, storyboardMarkdown));
        }
        return shotPlans.stream().map(StoryboardShotPlan::videoPrompt).toList();
    }

    public List<StoryboardShotPlan> buildStoryboardShotPlans(TaskRecord task, String storyboardMarkdown) {
        List<StoryboardShotPlan> shotPlans = extractStoryboardShotPlans(storyboardMarkdown);
        if (!shotPlans.isEmpty()) {
            return shotPlans;
        }
        String fallbackPrompt = buildVisualPrompt(task, storyboardMarkdown);
        return List.of(new StoryboardShotPlan(1, "1", "", fallbackPrompt, fallbackPrompt, "", "static", "", fallbackPrompt, fallbackPrompt));
    }

    public List<String> buildStoryboardVideoPrompts(String storyboardMarkdown) {
        List<StoryboardShotPlan> shotPlans = extractStoryboardShotPlans(storyboardMarkdown);
        if (!shotPlans.isEmpty()) {
            return shotPlans.stream().map(StoryboardShotPlan::videoPrompt).toList();
        }
        String normalized = stringValue(storyboardMarkdown).replaceAll("\\s+", " ").trim();
        return normalized.isBlank() ? List.of() : List.of(truncateText(normalized, 1200));
    }

    public int resolveRequestedOutputCount(TaskRecord task, int storyboardClipCount) {
        int availableClipCount = Math.max(1, storyboardClipCount);
        if (task.requestSnapshot == null || task.requestSnapshot.outputCount().auto()) {
            return availableClipCount;
        }
        Integer requested = task.requestSnapshot.outputCount().count();
        if (requested == null) {
            return availableClipCount;
        }
        return Math.max(1, Math.min(requested, availableClipCount));
    }

    public Object requestSnapshotOutputCount(TaskRecord task) {
        if (task.requestSnapshot == null) {
            return "auto";
        }
        return task.requestSnapshot.outputCount().toValue();
    }

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

    public List<int[]> buildClipDurationPlan(TaskRecord task, int defaultDurationSeconds, int clipCount, String storyboardMarkdown) {
        int normalizedClipCount = Math.max(1, clipCount);
        int totalMin = Math.max(1, task.minDurationSeconds > 0 ? task.minDurationSeconds : defaultDurationSeconds);
        int totalMax = Math.max(totalMin, task.maxDurationSeconds > 0 ? task.maxDurationSeconds : defaultDurationSeconds);
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
            ? 1
            : Math.max(1, Math.round((float) Math.max(unresolvedClipCount, totalMin - scriptedMinSum) / unresolvedClipCount));
        int globalMax = unresolvedClipCount == 0
            ? globalMin
            : Math.max(globalMin, Math.round((float) Math.max(unresolvedClipCount, totalMax - scriptedMaxSum) / unresolvedClipCount));
        List<int[]> plan = new ArrayList<>();
        for (int index = 0; index < normalizedClipCount; index++) {
            boolean scripted = index < ranges.size();
            int clipMin = scripted ? Math.max(1, ranges.get(index)[0]) : globalMin;
            int clipMax = scripted ? Math.max(clipMin, ranges.get(index)[1]) : globalMax;
            int clipTarget = scripted
                ? clipMin
                : Math.max(clipMin, Math.min(clipMax, Math.round((clipMin + clipMax) / 2.0f)));
            plan.add(new int[] {clipTarget, clipMin, clipMax});
        }
        return plan;
    }

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

    public String buildFallbackStoryboard(TaskRecord task, int durationSeconds, int width, int height) {
        return String.join("\n",
            "# 分镜脚本",
            "",
            "- 任务标题: " + task.title,
            "- 画幅: " + task.aspectRatio + " (" + width + "x" + height + ")",
            "- 时长: " + durationSeconds + " 秒",
            "",
            "## 场景摘要",
            truncateText(!task.creativePrompt.isBlank() ? task.creativePrompt : task.transcriptText, 360)
        );
    }

    private String buildCompactPromptContext(TaskRecord task, String storyboardMarkdown) {
        String storyboardContext = extractStoryboardContextSummary(storyboardMarkdown);
        if (!storyboardContext.isBlank()) {
            return storyboardContext;
        }
        String fallback = !task.creativePrompt.isBlank()
            ? task.creativePrompt
            : (!task.transcriptText.isBlank() ? task.transcriptText : task.title);
        return truncateText(fallback.replaceAll("\\s+", " ").trim(), 320);
    }

    private String extractStoryboardContextSummary(String storyboardMarkdown) {
        String normalized = stringValue(storyboardMarkdown);
        if (normalized.isBlank()) {
            return "";
        }
        List<String> lines = List.of(normalized.split("\\R"));
        List<String> summaryLines = new ArrayList<>();
        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            if (stripped.isBlank()) {
                continue;
            }
            if (stripped.startsWith("|")) {
                break;
            }
            String cleaned = stripped
                .replaceAll("^#{1,6}\\s*", "")
                .replaceAll("^[-*]\\s*", "")
                .replace("**", "")
                .replace("<br>", " ")
                .replace("<br/>", " ")
                .replace("<br />", " ")
                .replaceAll("\\s+", " ")
                .trim();
            if (cleaned.isBlank()) {
                continue;
            }
            summaryLines.add(cleaned);
            if (String.join("；", summaryLines).length() >= 320) {
                break;
            }
        }
        return truncateText(String.join("；", summaryLines), 320);
    }

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
            if (cells.size() < 4 || isDividerRow(cells) || schema.isHeaderRow(cells)) {
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
            String unifiedPrompt = unifyStoryboardPrompt(visual, dynamic);
            String characterAppearance = schema.cell(cells, schema.characterAppearanceIndex(), -1);
            String action = schema.cell(cells, schema.actionIndex(), -1);
            String emotion = schema.cell(cells, schema.emotionIndex(), -1);
            String lighting = schema.cell(cells, schema.lightingIndex(), -1);
            String atmosphere = schema.cell(cells, schema.atmosphereIndex(), -1);
            String dialogue = normalizeStoryboardPromptValue(schema.cell(cells, schema.dialogueIndex(), -1));
            String audio = normalizeStoryboardPromptValue(schema.cell(cells, schema.audioIndex(), -1));
            String durationHint = schema.cell(cells, schema.durationIndex(), legacyDurationFallbackIndex);
            String firstFramePrompt = explicitFirstFrame;
            String lastFramePrompt = explicitLastFrame;
            String motion = explicitMotion;
            if (firstFramePrompt.isBlank()) {
                firstFramePrompt = buildLegacyFirstFramePrompt(scene, time, shotSpec, visual, characterAppearance, lighting, atmosphere);
            }
            if (lastFramePrompt.isBlank()) {
                lastFramePrompt = buildLegacyLastFramePrompt(scene, unifiedPrompt, action, emotion);
            }
            if (motion.isBlank()) {
                motion = normalizeStoryboardPromptValue(action);
            }
            if (cameraMovement.isBlank()) {
                cameraMovement = "static";
            }
            String imagePrompt = sequentialIndex == 1 ? firstNonBlank(firstFramePrompt, lastFramePrompt, unifiedPrompt) : "";
            String videoPrompt = buildContinuousClipPrompt(lastFramePrompt, motion, cameraMovement, dialogue, audio);
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

        String currentTitle = "";
        List<String> currentLines = new ArrayList<>();
        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            Matcher matcher = SHOT_HEADING_PATTERN.matcher(stripped);
            if (matcher.matches()) {
                flushHeadingShot(shotPlans, currentTitle, currentLines);
                currentTitle = stringValue(matcher.group("title"));
                currentLines = new ArrayList<>();
                continue;
            }
            if (!currentTitle.isBlank()) {
                currentLines.add(rawLine);
            }
        }
        flushHeadingShot(shotPlans, currentTitle, currentLines);
        return shotPlans.isEmpty() ? List.of() : shotPlans;
    }

    private void flushHeadingShot(List<StoryboardShotPlan> shotPlans, String currentTitle, List<String> currentLines) {
        String title = stringValue(currentTitle);
        String body = stripNarrationVoiceoverText(String.join(" ", currentLines).replaceAll("\\s+", " ").trim());
        String lastFramePrompt;
        if (!title.isBlank() && !body.isBlank()) {
            lastFramePrompt = "same scene, same character, " + body;
        } else if (!title.isBlank()) {
            lastFramePrompt = title;
        } else {
            lastFramePrompt = body;
        }
        if (!lastFramePrompt.isBlank()) {
            int sequentialIndex = shotPlans.size() + 1;
            String videoPrompt = buildContinuousClipPrompt(lastFramePrompt, "", "static", "", "");
            shotPlans.add(new StoryboardShotPlan(
                sequentialIndex,
                String.valueOf(sequentialIndex),
                title,
                sequentialIndex == 1 ? lastFramePrompt : "",
                lastFramePrompt,
                "",
                "static",
                "",
                sequentialIndex == 1 ? lastFramePrompt : "",
                videoPrompt
            ));
        }
    }

    private int[] normalizeClipDurationRange(
        List<Integer> supportedDurations,
        int targetDurationSeconds,
        int minDurationSeconds,
        int maxDurationSeconds
    ) {
        int normalizedTarget = Math.max(1, targetDurationSeconds);
        int normalizedMin = Math.max(1, Math.min(minDurationSeconds, maxDurationSeconds));
        int normalizedMax = Math.max(normalizedMin, Math.max(minDurationSeconds, maxDurationSeconds));
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

    private int[] parseDurationRangeHint(String text) {
        String normalized = stringValue(text);
        if (normalized.isBlank()) {
            return null;
        }
        Matcher rangeMatcher = SCRIPT_DURATION_RANGE_PATTERN.matcher(normalized);
        if (rangeMatcher.find()) {
            int left = safeRoundedSeconds(rangeMatcher.group("left"));
            int right = safeRoundedSeconds(rangeMatcher.group("right"));
            int low = Math.max(1, Math.min(left, right));
            int high = Math.max(low, Math.max(left, right));
            return new int[] {low, high};
        }
        Matcher valueMatcher = SCRIPT_DURATION_VALUE_PATTERN.matcher(normalized);
        if (valueMatcher.find()) {
            int value = safeRoundedSeconds(valueMatcher.group("value"));
            return new int[] {value, value};
        }
        Matcher plainRangeMatcher = PLAIN_DURATION_RANGE_PATTERN.matcher(normalized);
        if (plainRangeMatcher.find()) {
            int left = safeRoundedSeconds(plainRangeMatcher.group("left"));
            int right = safeRoundedSeconds(plainRangeMatcher.group("right"));
            int low = Math.max(1, Math.min(left, right));
            int high = Math.max(low, Math.max(left, right));
            return new int[] {low, high};
        }
        Matcher plainValueMatcher = PLAIN_DURATION_VALUE_PATTERN.matcher(normalized);
        if (plainValueMatcher.find()) {
            int value = safeRoundedSeconds(plainValueMatcher.group("value"));
            return new int[] {value, value};
        }
        return null;
    }

    private int safeRoundedSeconds(String value) {
        try {
            return Math.max(1, Math.min(120, (int) Math.round(Double.parseDouble(stringValue(value)))));
        } catch (NumberFormatException ex) {
            return 1;
        }
    }

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

    private boolean looksLikeHeaderRow(List<String> cells) {
        for (String cell : cells) {
            String normalized = normalizeStoryboardHeader(cell);
            if (normalized.contains("shot") || normalized.contains("镜号") || normalized.contains("景别")
                || normalized.contains("运镜") || normalized.contains("镜头参数") || normalized.contains("画面") || normalized.contains("visual")
                || normalized.contains("audio") || normalized.contains("duration") || normalized.contains("时长")
                || normalized.contains("剧情摘要") || normalized.contains("seedream") || normalized.contains("seedance")
                || normalized.contains("scene") || normalized.contains("time") || normalized.contains("lighting")
                || normalized.contains("atmosphere") || normalized.contains("appearance") || normalized.contains("action")
                || normalized.contains("emotion") || normalized.contains("camera") || normalized.contains("continuity")) {
                return true;
            }
        }
        return false;
    }

    private String normalizeStoryboardHeader(String text) {
        return stringValue(text)
            .trim()
            .toLowerCase()
            .replaceAll("[\\s_\\-()（）/\\\\+:：·,.，]", "");
    }

    private String joinNonBlank(String delimiter, String... values) {
        List<String> parts = new ArrayList<>();
        for (String value : values) {
            String normalized = stringValue(value);
            if (!normalized.isBlank()) {
                parts.add(normalized);
            }
        }
        return String.join(delimiter, parts);
    }

    private String unifyStoryboardPrompt(String visual, String dynamic) {
        String normalizedVisual = normalizeStoryboardPromptValue(visual);
        String normalizedDynamic = normalizeStoryboardPromptValue(dynamic);
        if (normalizedVisual.isBlank()) {
            return normalizedDynamic;
        }
        if (normalizedDynamic.isBlank()) {
            return normalizedVisual;
        }
        if (normalizedVisual.equalsIgnoreCase(normalizedDynamic)) {
            return normalizedVisual;
        }
        return truncateText(normalizedVisual + "；动态延展：" + normalizedDynamic, 1200);
    }

    private String normalizeStoryboardPromptValue(String value) {
        return stringValue(value)
            .replace("<br>", " ")
            .replace("<br/>", " ")
            .replace("<br />", " ")
            .replaceAll("\\s+", " ")
            .trim();
    }

    private String buildLegacyFirstFramePrompt(
        String scene,
        String time,
        String shotSpec,
        String visual,
        String characterAppearance,
        String lighting,
        String atmosphere
    ) {
        String normalizedVisual = normalizeStoryboardPromptValue(visual);
        return truncateText(joinNonBlank(", ",
            normalizedVisual,
            normalizeStoryboardPromptValue(characterAppearance),
            normalizedVisual.isBlank() && !scene.isBlank() ? scene : "",
            normalizedVisual.isBlank() && !time.isBlank() ? time : "",
            normalizeStoryboardPromptValue(shotSpec),
            normalizeStoryboardPromptValue(lighting),
            normalizeStoryboardPromptValue(atmosphere)
        ), 1200);
    }

    private String buildLegacyLastFramePrompt(String scene, String unifiedPrompt, String action, String emotion) {
        String normalizedPrompt = normalizeStoryboardPromptValue(unifiedPrompt);
        return truncateText(joinNonBlank(", ",
            normalizedPrompt,
            normalizedPrompt.isBlank() && !scene.isBlank() ? scene : "",
            normalizeStoryboardPromptValue(action),
            normalizeStoryboardPromptValue(emotion)
        ), 1200);
    }

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

    private String dialogueInstruction(String dialogue) {
        String normalized = normalizeStoryboardPromptValue(dialogue);
        if (normalized.isBlank()) {
            return "";
        }
        if (normalized.startsWith("独白：") || normalized.startsWith("独白:")) {
            return "可听见的人声独白：" + normalized + "；独白放在镜头中段，前0.5秒与后0.5秒保持无人声，仅保留动作或环境声缓冲。";
        }
        if (normalized.contains("“") || normalized.contains("\"") || normalized.contains("：") || normalized.contains(":")) {
            return "可听见的人声对白：" + normalized + "；对白放在镜头中段，前0.5秒与后0.5秒保持无人声，仅保留动作或环境声缓冲。";
        }
        return "可听见的人声独白：独白：" + normalized + "；独白放在镜头中段，前0.5秒与后0.5秒保持无人声，仅保留动作或环境声缓冲。";
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            String normalized = stringValue(value);
            if (!normalized.isBlank()) {
                return normalized;
            }
        }
        return "";
    }

    private boolean isDividerRow(List<String> cells) {
        for (String cell : cells) {
            if (!cell.matches("[:\\-\\s]*")) {
                return false;
            }
        }
        return true;
    }

    private String stripNarrationVoiceoverText(String text) {
        String normalized = stringValue(text);
        String lowered = normalized.toLowerCase();
        if (!(normalized.contains("旁白") || normalized.contains("画外音") || normalized.contains("解说")
            || lowered.contains("narration") || lowered.contains("voiceover") || lowered.contains("voice over"))) {
            return normalized;
        }
        String cleaned = normalized.replaceAll("[（(]\\s*(?:旁白|画外音|解说|narration|voice\\s*over|voiceover)\\s*[)）]\\s*[:：]?\\s*", "");
        String[] segments = cleaned.split("[；;。!！?？\\n]+");
        List<String> kept = new ArrayList<>();
        for (String segment : segments) {
            String candidate = segment.trim();
            String loweredCandidate = candidate.toLowerCase();
            if (candidate.isBlank()) {
                continue;
            }
            if (candidate.contains("旁白") || candidate.contains("画外音") || candidate.contains("解说")
                || loweredCandidate.contains("narration") || loweredCandidate.contains("voiceover") || loweredCandidate.contains("voice over")) {
                continue;
            }
            kept.add(candidate);
        }
        return String.join("；", kept).replaceAll("^[，,；;。\\s]+|[，,；;。\\s]+$", "");
    }

    private String buildVisualPrompt(TaskRecord task, String storyboardMarkdown) {
        String base = !task.creativePrompt.isBlank() ? task.creativePrompt : (!task.transcriptText.isBlank() ? task.transcriptText : task.title);
        String storyboardSnippet = truncateText(storyboardMarkdown, 280);
        return truncateText(base + "\n\n参考分镜语义：" + storyboardSnippet, 640);
    }

    private GenerationRequestSnapshot requestSnapshot(TaskRecord task) {
        return task == null ? null : task.requestSnapshot;
    }

    private String truncateText(String value, int maxLength) {
        String normalized = stringValue(value);
        if (normalized.length() <= maxLength) {
            return normalized;
        }
        return normalized.substring(0, Math.max(0, maxLength - 1)).trim() + "…";
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

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
        Integer characterAppearanceIndex,
        Integer actionIndex,
        Integer emotionIndex,
        Integer lightingIndex,
        Integer atmosphereIndex,
        Integer dialogueIndex,
        Integer audioIndex,
        Integer durationIndex
    ) {
        static StoryboardTableSchema empty() {
            return new StoryboardTableSchema(List.of(), null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null);
        }

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
                resolve(headers, "统一提示词", "统一画面提示词", "镜头提示词", "cinematicvisualdescription", "visualdescription", "visualcontent", "视觉描述", "画面细节描述", "画面描述", "visualprompt", "seedream提示词", "seedream", "关键帧", "visual"),
                resolve(headers, "统一提示词", "统一画面提示词", "镜头提示词", "seedance提示词", "seedance", "动态与运镜", "动态", "衔接逻辑", "continuity", "motion"),
                resolve(headers, "characterappearance", "appearance", "人物外观", "角色外观"),
                resolve(headers, "action", "动作"),
                resolve(headers, "sentiment", "emotion", "情绪", "情感分析", "感情分析", "情感", "感情"),
                resolve(headers, "lighting", "光线"),
                resolve(headers, "atmosphere", "氛围"),
                resolve(headers, "dialogue", "独白", "对话", "对白", "台词", "字幕"),
                resolve(headers, "audio", "音效", "bgm", "sfx", "旁白", "画外音", "声音与对白"),
                resolve(headers, "duration", "时长", "秒")
            );
        }

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

        String cell(List<String> cells, Integer index, int fallbackIndex) {
            int resolvedIndex = index != null ? index : fallbackIndex;
            if (resolvedIndex < 0 || resolvedIndex >= cells.size()) {
                return "";
            }
            Object value = cells.get(resolvedIndex);
            return value == null ? "" : String.valueOf(value).trim();
        }
    }

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
