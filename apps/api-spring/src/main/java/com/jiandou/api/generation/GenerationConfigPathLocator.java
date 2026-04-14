package com.jiandou.api.generation;

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

@Service
public class GenerationConfigPathLocator {

    private static final Logger log = LoggerFactory.getLogger(GenerationConfigPathLocator.class);

    private final Environment environment;

    public GenerationConfigPathLocator(Environment environment) {
        this.environment = environment;
    }

    public LocatedConfig locateAppConfig() {
        List<Path> checkedCandidates = new ArrayList<>();
        boolean explicitConfigRequested = hasConfiguredValue("JIANDOU_CONFIG_FILE", "jiandou.config.file", "JIANDOU_CONFIG_PATH", "jiandou.config.path")
            || hasConfiguredValue("JIANDOU_CONFIG_DIR", "jiandou.config.dir")
            || hasConfiguredValue("spring.config.additional-location", "SPRING_CONFIG_ADDITIONAL_LOCATION")
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

    private List<Path> springDefaultExternalCandidates() {
        Path cwd = currentWorkingDirectory();
        List<Path> candidates = new ArrayList<>(configFileCandidates(cwd.resolve("config")));
        candidates.addAll(configFileCandidates(cwd));
        return candidates.stream().distinct().toList();
    }

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

    private Path currentWorkingDirectory() {
        return Paths.get(firstNonBlank(System.getProperty("user.dir"), ".")).toAbsolutePath().normalize();
    }

    private List<Path> configFileCandidates(Path directory) {
        Path normalizedDir = directory.toAbsolutePath().normalize();
        List<Path> candidates = new ArrayList<>();
        candidates.add(normalizedDir.resolve("app.yml").normalize());
        candidates.add(normalizedDir.resolve("app.yaml").normalize());
        return candidates;
    }

    private String stripOptionalPrefix(String value) {
        if (value.startsWith("optional:")) {
            return value.substring("optional:".length()).trim();
        }
        return value;
    }

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

    private boolean startsWithConfigPrefix(String value) {
        String normalized = value.replace('\\', '/');
        return normalized.startsWith("config/");
    }

    private boolean isRegularFile(Path path) {
        return path != null && Files.isRegularFile(path.toAbsolutePath().normalize());
    }

    private String property(String key) {
        String value = environment.getProperty(key);
        return value == null ? "" : value.trim();
    }

    private boolean hasConfiguredValue(String... keys) {
        for (String key : keys) {
            if (!property(key).isBlank()) {
                return true;
            }
        }
        return false;
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    public record LocatedConfig(
        Path configFile,
        Path configDir,
        Path projectRoot,
        String source,
        String detail
    ) {}
}
