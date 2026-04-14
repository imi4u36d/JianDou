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
        "(?<left>\\d{1,3}(?:\\.\\d+)?)\\s*(?:-|~|～|—|到)\\s*(?<right>\\d{1,3}(?:\\.\\d+)?)\\s*(?:s|秒)",
        Pattern.CASE_INSENSITIVE
    );
    private static final Pattern SCRIPT_DURATION_VALUE_PATTERN = Pattern.compile(
        "(?<![\\d.])(?<value>\\d{1,3}(?:\\.\\d+)?)\\s*(?:s|秒)(?![a-zA-Z])",
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
        String globalContext = buildCompactPromptContext(task, storyboardMarkdown);
        List<String> shotPrompts = extractStoryboardShotPrompts(storyboardMarkdown);
        if (shotPrompts.isEmpty()) {
            return List.of(buildVisualPrompt(task, storyboardMarkdown));
        }
        List<String> prompts = new ArrayList<>();
        int total = shotPrompts.size();
        for (int index = 0; index < total; index++) {
            String continuityHint = index == 0 ? "建立场景与人物关系。" : "承接上一镜动作与情绪，衔接自然。";
            String composed = truncateText(
                """
                当前任务：
                按剧情顺序仅生成第 %d/%d 镜，禁止跨镜头合并，禁止补写未给出的剧情。

                当前镜头拆解：
                %s

                全片连续性基线：
                %s

                执行要求：
                1. 画面描述必须具体到人物造型、动作过程、表情变化、视线方向、主体与环境关系、前景中景后景、道具、光线、氛围颗粒。
                2. 不要做长时间空镜、站桩、发呆、纯环境展示；镜头内必须有持续可见的动作或情绪推进。
                3. 如果镜头较长，必须让动作、调度、表情或构图产生阶段性变化，不能只有一个静止状态。
                4. 严格保留对白归属与剧情语义，不得把一句台词分配给错误角色。
                5. %s
                6. 音频要求：保留人物对白与环境音，禁止旁白、画外音、解说配音。
                """.formatted(index + 1, total, shotPrompts.get(index), globalContext, continuityHint),
                1800
            );
            prompts.add(composed);
        }
        return prompts;
    }

    public List<String> buildStoryboardVideoPrompts(String storyboardMarkdown) {
        List<String> fallbackPrompts = extractStoryboardShotPrompts(storyboardMarkdown);
        List<String> prompts = extractStoryboardShotDynamicPrompts(storyboardMarkdown);
        if (!prompts.isEmpty() && prompts.size() == fallbackPrompts.size()) {
            return prompts;
        }
        if (!fallbackPrompts.isEmpty()) {
            return fallbackPrompts;
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
            int clipTarget = Math.max(clipMin, Math.min(clipMax, Math.round((clipMin + clipMax) / 2.0f)));
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

    private List<String> extractStoryboardShotPrompts(String storyboardMarkdown) {
        String normalized = stringValue(storyboardMarkdown);
        if (normalized.isBlank()) {
            return List.of();
        }
        List<String> lines = List.of(normalized.split("\\R"));
        StoryboardTableSchema schema = detectStoryboardTableSchema(lines);
        List<String> shotPrompts = new ArrayList<>();

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
                shotIndex = String.valueOf(shotPrompts.size() + 1);
            }
            int legacyCameraFallbackIndex = schema.headerCells().isEmpty() ? 2 : -1;
            int legacyDurationFallbackIndex = schema.headerCells().isEmpty() ? cells.size() - 1 : -1;
            String scene = schema.cell(cells, schema.sceneIndex(), 1);
            String shotSpec = schema.cell(cells, schema.shotSpecIndex(), legacyCameraFallbackIndex);
            String movement = schema.cell(cells, schema.movementIndex(), legacyCameraFallbackIndex);
            String camera = joinNonBlank(" / ", shotSpec, movement);
            String visual = schema.cell(cells, schema.visualIndex(), 3);
            String dynamic = schema.cell(cells, schema.dynamicIndex(), -1);
            String dialogue = stripNarrationVoiceoverText(schema.cell(cells, schema.dialogueIndex(), 4));
            String audio = schema.cell(cells, schema.audioIndex(), cells.size() > 5 ? 5 : 4);
            String durationHint = schema.cell(cells, schema.durationIndex(), legacyDurationFallbackIndex);
            List<String> parts = new ArrayList<>();
            parts.add("镜头编号：" + shotIndex);
            if (!scene.isBlank()) {
                parts.add("剧情节点：" + scene);
            }
            if (!camera.isBlank()) {
                parts.add("镜头语言：" + camera);
            }
            if (!visual.isBlank()) {
                parts.add("Seedream提示词：" + visual);
            }
            if (!dynamic.isBlank()) {
                parts.add("Seedance提示词：" + dynamic);
            }
            if (!dialogue.isBlank()) {
                parts.add("人物对白：" + dialogue);
            }
            if (!audio.isBlank()) {
                parts.add("声音设计：" + audio);
            }
            if (!durationHint.isBlank()) {
                parts.add("建议时长：" + durationHint);
            }
            shotPrompts.add(truncateText(String.join("\n", parts), 900));
        }
        if (!shotPrompts.isEmpty()) {
            return shotPrompts;
        }

        String currentTitle = "";
        List<String> currentLines = new ArrayList<>();
        for (String rawLine : lines) {
            String stripped = rawLine.trim();
            Matcher matcher = SHOT_HEADING_PATTERN.matcher(stripped);
            if (matcher.matches()) {
                flushHeadingShot(shotPrompts, currentTitle, currentLines);
                currentTitle = stringValue(matcher.group("title"));
                currentLines = new ArrayList<>();
                continue;
            }
            if (!currentTitle.isBlank()) {
                currentLines.add(rawLine);
            }
        }
        flushHeadingShot(shotPrompts, currentTitle, currentLines);
        return shotPrompts.isEmpty() ? List.of() : shotPrompts;
    }

    private List<String> extractStoryboardShotDynamicPrompts(String storyboardMarkdown) {
        String normalized = stringValue(storyboardMarkdown);
        if (normalized.isBlank()) {
            return List.of();
        }
        List<String> lines = List.of(normalized.split("\\R"));
        StoryboardTableSchema schema = detectStoryboardTableSchema(lines);
        List<String> dynamicPrompts = new ArrayList<>();

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
            String dynamic = schema.cell(cells, schema.dynamicIndex(), -1)
                .replace("<br>", " ")
                .replace("<br/>", " ")
                .replace("<br />", " ")
                .replaceAll("\\s+", " ")
                .trim();
            if (!dynamic.isBlank()) {
                dynamicPrompts.add(truncateText(dynamic, 1200));
            }
        }
        return dynamicPrompts;
    }

    private void flushHeadingShot(List<String> shotPrompts, String currentTitle, List<String> currentLines) {
        String title = stringValue(currentTitle);
        String body = stripNarrationVoiceoverText(String.join(" ", currentLines).replaceAll("\\s+", " ").trim());
        String merged;
        if (!title.isBlank() && !body.isBlank()) {
            merged = "剧情节点：" + title + "；画面描述：" + body;
        } else if (!title.isBlank()) {
            merged = "剧情节点：" + title;
        } else {
            merged = body;
        }
        if (!merged.isBlank()) {
            shotPrompts.add(truncateText(merged, 900));
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
                || normalized.contains("运镜") || normalized.contains("画面") || normalized.contains("visual")
                || normalized.contains("audio") || normalized.contains("duration") || normalized.contains("时长")
                || normalized.contains("剧情摘要") || normalized.contains("seedream") || normalized.contains("seedance")) {
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
        Integer shotSpecIndex,
        Integer movementIndex,
        Integer visualIndex,
        Integer dynamicIndex,
        Integer dialogueIndex,
        Integer audioIndex,
        Integer durationIndex
    ) {
        static StoryboardTableSchema empty() {
            return new StoryboardTableSchema(List.of(), null, null, null, null, null, null, null, null, null);
        }

        static StoryboardTableSchema fromHeader(List<String> headers) {
            return new StoryboardTableSchema(
                List.copyOf(headers),
                resolve(headers, "shotno", "shot", "镜号"),
                resolve(headers, "剧情摘要", "剧情节点", "场景", "scene", "summary"),
                resolve(headers, "shotspec", "景别角度", "景别", "镜头语言", "shotsize", "angle"),
                resolve(headers, "movement", "运镜"),
                resolve(headers, "visualcontent", "视觉描述", "画面细节描述", "画面描述", "visualprompt", "seedream提示词", "seedream", "关键帧", "visual"),
                resolve(headers, "seedance提示词", "seedance", "动态与运镜", "动态", "motion"),
                resolve(headers, "dialogue", "对白", "台词", "字幕"),
                resolve(headers, "audio", "音效", "bgm", "sfx", "旁白", "画外音"),
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
}
