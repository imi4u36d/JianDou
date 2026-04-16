package com.jiandou.api.generation.runtime;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;

/**
 * 生成配置路径Locator。
 */
@Service
public class GenerationConfigPathLocator {

    private static final Logger log = LoggerFactory.getLogger(GenerationConfigPathLocator.class);

    private final Environment environment;

    /**
     * 创建新的生成配置路径Locator。
     * @param environment environment值
     */
    public GenerationConfigPathLocator(Environment environment) {
        this.environment = environment;
    }

    /**
     * 处理locateApp配置。
     * @return 处理结果
     */
    public LocatedConfig locateAppConfig() {
        List<Path> checkedCandidates = new ArrayList<>();
        boolean explicitConfigRequested = hasConfiguredValue("JIANDOU_CONFIG_FILE", "jiandou.config.file", "JIANDOU_CONFIG_PATH", "jiandou.config.path")
            /**
             * 检查是否Configured值。
             * @param "JIANDOU_CONFIG_DIR" "JIANDOU配置DIR"值
             * @param "jiandou.config.dir" "jiandou.config.dir"值
             * @return 是否满足条件
             */
            || hasConfiguredValue("JIANDOU_CONFIG_DIR", "jiandou.config.dir")
            /**
             * 检查是否Configured值。
             * @param "spring.config.additional-location" "spring.config.additionallocation"值
             * @param "SPRING_CONFIG_ADDITIONAL_LOCATION" "SPRING配置ADDITIONALLOCATION"值
             * @return 是否满足条件
             */
            || hasConfiguredValue("spring.config.additional-location", "SPRING_CONFIG_ADDITIONAL_LOCATION")
            /**
             * 检查是否Configured值。
             * @param "spring.config.location" "spring.config.location"值
             * @param "SPRING_CONFIG_LOCATION" "SPRING配置LOCATION"值
             * @return 是否满足条件
             */
            || hasConfiguredValue("spring.config.location", "SPRING_CONFIG_LOCATION");
        Path explicitFile = resolveExplicitConfigFile(checkedCandidates);
        if (explicitFile != null) {
            return buildLocatedConfig(explicitFile, "explicit-file");
        }
        Path fromExplicitDir = resolveConfigFromExplicitDir(checkedCandidates);
        if (fromExplicitDir != null) {
            return buildLocatedConfig(fromExplicitDir, "explicit-dir");
        }
        Path fromSpringAdditional = resolveFromSpringLocation(
            firstNonBlank(property("spring.config.additional-location"), property("SPRING_CONFIG_ADDITIONAL_LOCATION")),
            "spring.config.additional-location",
            checkedCandidates
        );
        if (fromSpringAdditional != null) {
            return buildLocatedConfig(fromSpringAdditional, "spring.config.additional-location");
        }
        Path fromSpringLocation = resolveFromSpringLocation(
            firstNonBlank(property("spring.config.location"), property("SPRING_CONFIG_LOCATION")),
            "spring.config.location",
            checkedCandidates
        );
        if (fromSpringLocation != null) {
            return buildLocatedConfig(fromSpringLocation, "spring.config.location");
        }
        for (Path candidate : springDefaultExternalCandidates()) {
            checkedCandidates.add(candidate);
            if (isRegularFile(candidate)) {
                return buildLocatedConfig(candidate, "spring-default");
            }
        }
        if (!explicitConfigRequested) {
            for (Path candidate : ancestorExternalCandidates()) {
                checkedCandidates.add(candidate);
                if (isRegularFile(candidate)) {
                    return buildLocatedConfig(candidate, "parent-default");
                }
            }
        }
        String detail = describeCheckedCandidates(checkedCandidates);
        log.warn("Generation config file not found; {}", detail);
        return new LocatedConfig(null, null, null, "missing", detail);
    }

    /**
     * 处理解析路径。
     * @param configuredPath configured路径值
     * @return 处理结果
     */
    public Path resolvePath(String configuredPath) {
        String normalized = trimToEmpty(configuredPath);
        if (normalized.isBlank()) {
            return null;
        }
        if (normalized.startsWith("classpath:")) {
            log.warn("Classpath resource cannot be resolved as filesystem path: {}", normalized);
            return null;
        }
        Path path = Paths.get(normalized);
        if (path.isAbsolute()) {
            return path.normalize();
        }
        LocatedConfig locatedConfig = locateAppConfig();
        if (startsWithConfigPrefix(normalized) && locatedConfig.projectRoot() != null) {
            return locatedConfig.projectRoot().resolve(path).normalize();
        }
        if (locatedConfig.configDir() != null) {
            return locatedConfig.configDir().resolve(path).normalize();
        }
        return Paths.get("").toAbsolutePath().normalize().resolve(path).normalize();
    }

    /**
     * 解析模型 secrets 覆盖文件路径。
     * @return 处理结果
     */
    public Path resolveSecretsConfigPath() {
        LocatedConfig locatedConfig = locateAppConfig();
        if (locatedConfig.configDir() == null) {
            return null;
        }
        return locatedConfig.configDir().resolve("app.secrets.yml").toAbsolutePath().normalize();
    }

    /**
     * 处理解析Explicit配置文件。
     * @param checkedCandidates checkedCandidates值
     * @return 处理结果
     */
    private Path resolveExplicitConfigFile(List<Path> checkedCandidates) {
        for (String key : List.of("JIANDOU_CONFIG_FILE", "jiandou.config.file", "JIANDOU_CONFIG_PATH", "jiandou.config.path")) {
            String value = property(key);
            if (value.isBlank()) {
                continue;
            }
            Path candidate = Paths.get(value);
            checkedCandidates.add(candidate.toAbsolutePath().normalize());
            if (isRegularFile(candidate)) {
                return candidate.toAbsolutePath().normalize();
            }
            log.warn("Ignored non-existent config file from {}={}", key, value);
        }
        return null;
    }

    /**
     * 处理解析配置FromExplicitDir。
     * @param checkedCandidates checkedCandidates值
     * @return 处理结果
     */
    private Path resolveConfigFromExplicitDir(List<Path> checkedCandidates) {
        for (String key : List.of("JIANDOU_CONFIG_DIR", "jiandou.config.dir")) {
            String value = property(key);
            if (value.isBlank()) {
                continue;
            }
            Path base = Paths.get(value).toAbsolutePath().normalize();
            for (Path candidate : configFileCandidates(base)) {
                checkedCandidates.add(candidate);
                if (isRegularFile(candidate)) {
                    return candidate;
                }
            }
            log.warn("Ignored config dir without app.yml/app.yaml from {}={}", key, value);
        }
        return null;
    }

    /**
     * 处理解析FromSpringLocation。
     * @param location location值
     * @param sourceKey 来源Key值
     * @param checkedCandidates checkedCandidates值
     * @return 处理结果
     */
    private Path resolveFromSpringLocation(String location, String sourceKey, List<Path> checkedCandidates) {
        if (trimToEmpty(location).isBlank()) {
            return null;
        }
        for (String token : location.split(",")) {
            String raw = stripOptionalPrefix(trimToEmpty(token));
            if (raw.isBlank() || raw.startsWith("classpath:")) {
                continue;
            }
            String cleaned = raw.startsWith("file:") ? raw.substring("file:".length()) : raw;
            if (cleaned.contains("*")) {
                continue;
            }
            Path candidate = Paths.get(cleaned);
            boolean treatAsDir = raw.endsWith("/") || raw.endsWith("\\") || Files.isDirectory(candidate);
            if (treatAsDir) {
                for (Path configCandidate : configFileCandidates(candidate)) {
                    checkedCandidates.add(configCandidate);
                    if (isRegularFile(configCandidate)) {
                        return configCandidate;
                    }
                }
                continue;
            }
            checkedCandidates.add(candidate.toAbsolutePath().normalize());
            if (isRegularFile(candidate)) {
                return candidate.toAbsolutePath().normalize();
            }
        }
        log.debug("No usable config file found in {}", sourceKey);
        return null;
    }

    /**
     * 处理spring默认ExternalCandidates。
     * @return 处理结果
     */
    private List<Path> springDefaultExternalCandidates() {
        Path cwd = currentWorkingDirectory();
        List<Path> candidates = new ArrayList<>(configFileCandidates(cwd.resolve("config")));
        candidates.addAll(configFileCandidates(cwd));
        return candidates.stream().distinct().toList();
    }

    /**
     * 处理ancestorExternalCandidates。
     * @return 处理结果
     */
    private List<Path> ancestorExternalCandidates() {
        List<Path> candidates = new ArrayList<>();
        Path current = currentWorkingDirectory().getParent();
        while (current != null) {
            candidates.addAll(configFileCandidates(current.resolve("config")));
            candidates.addAll(configFileCandidates(current));
            current = current.getParent();
        }
        return candidates.stream().distinct().toList();
    }

    /**
     * 处理currentWorkingDirectory。
     * @return 处理结果
     */
    private Path currentWorkingDirectory() {
        return Paths.get(firstNonBlank(System.getProperty("user.dir"), ".")).toAbsolutePath().normalize();
    }

    /**
     * 处理配置文件Candidates。
     * @param directory directory值
     * @return 处理结果
     */
    private List<Path> configFileCandidates(Path directory) {
        Path normalizedDir = directory.toAbsolutePath().normalize();
        List<Path> candidates = new ArrayList<>();
        candidates.add(normalizedDir.resolve("app.yml").normalize());
        candidates.add(normalizedDir.resolve("app.yaml").normalize());
        return candidates;
    }

    /**
     * 处理条带OptionalPrefix。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String stripOptionalPrefix(String value) {
        if (value.startsWith("optional:")) {
            return value.substring("optional:".length()).trim();
        }
        return value;
    }

    /**
     * 处理describeCheckedCandidates。
     * @param checkedCandidates checkedCandidates值
     * @return 处理结果
     */
    private String describeCheckedCandidates(List<Path> checkedCandidates) {
        if (checkedCandidates.isEmpty()) {
            return "no candidate config files were provided";
        }
        Set<Path> distinct = new LinkedHashSet<>(checkedCandidates);
        String joined = distinct.stream()
            .limit(12)
            .map(Path::toString)
            .collect(Collectors.joining(", "));
        if (distinct.size() > 12) {
            joined = joined + ", ...";
        }
        return "checked config candidates: " + joined;
    }

    /**
     * 构建Located配置。
     * @param configFile 配置文件值
     * @param sourceTag 来源Tag值
     * @return 处理结果
     */
    private LocatedConfig buildLocatedConfig(Path configFile, String sourceTag) {
        Path normalizedFile = configFile.toAbsolutePath().normalize();
        Path configDir = normalizedFile.getParent();
        Path projectRoot = configDir;
        if (configDir != null
            && configDir.getFileName() != null
            && "config".equalsIgnoreCase(configDir.getFileName().toString())
            && configDir.getParent() != null) {
            projectRoot = configDir.getParent();
        }
        return new LocatedConfig(
            normalizedFile,
            configDir,
            projectRoot,
            "file:" + normalizedFile,
            sourceTag
        );
    }

    /**
     * 检查是否startsWith配置Prefix。
     * @param value 待处理的值
     * @return 是否满足条件
     */
    private boolean startsWithConfigPrefix(String value) {
        String normalized = value.replace('\\', '/');
        return normalized.startsWith("config/");
    }

    /**
     * 检查是否Regular文件。
     * @param path 路径值
     * @return 是否满足条件
     */
    private boolean isRegularFile(Path path) {
        return path != null && Files.isRegularFile(path.toAbsolutePath().normalize());
    }

    /**
     * 处理property。
     * @param key key值
     * @return 处理结果
     */
    private String property(String key) {
        String value = environment.getProperty(key);
        return value == null ? "" : value.trim();
    }

    /**
     * 检查是否Configured值。
     * @param keys keys值
     * @return 是否满足条件
     */
    private boolean hasConfiguredValue(String... keys) {
        for (String key : keys) {
            if (!property(key).isBlank()) {
                return true;
            }
        }
        return false;
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
     * 处理trim转为Empty。
     * @param value 待处理的值
     * @return 处理结果
     */
    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    /**
     * 处理Located配置。
     * @param configFile 配置文件值
     * @param configDir 配置Dir值
     * @param projectRoot projectRoot值
     * @param source 来源值
     * @param detail 详情值
     * @return 处理结果
     */
    public record LocatedConfig(
        Path configFile,
        Path configDir,
        Path projectRoot,
        String source,
        String detail
    ) {}
}
