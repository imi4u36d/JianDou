package com.jiandou.api.config;

import java.nio.file.Path;
import java.nio.file.Paths;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * JianDou 本地存储配置。
 */
@ConfigurationProperties(prefix = "jiandou.storage")
public class JiandouStorageProperties {

    private String rootDir = "../../storage";
    private String uploadsDir = "uploads";
    private String generationRunsDir = "gen/_runs";

    public String getRootDir() {
        return rootDir;
    }

    public void setRootDir(String rootDir) {
        this.rootDir = rootDir == null ? "../../storage" : rootDir.trim();
    }

    public String getUploadsDir() {
        return uploadsDir;
    }

    public void setUploadsDir(String uploadsDir) {
        this.uploadsDir = uploadsDir == null ? "uploads" : uploadsDir.trim();
    }

    public String getGenerationRunsDir() {
        return generationRunsDir;
    }

    public void setGenerationRunsDir(String generationRunsDir) {
        this.generationRunsDir = generationRunsDir == null ? "gen/_runs" : generationRunsDir.trim();
    }

    public Path resolveRootDir() {
        return Paths.get(rootDir).toAbsolutePath().normalize();
    }

    public Path resolveUploadsDir() {
        return resolveWithinRoot(uploadsDir);
    }

    public Path resolveGenerationRunsDir() {
        return resolveWithinRoot(generationRunsDir);
    }

    public String buildPublicUrl(String relativePath) {
        String normalized = relativePath == null ? "" : relativePath.trim().replace('\\', '/');
        while (normalized.startsWith("/")) {
            normalized = normalized.substring(1);
        }
        return normalized.isBlank() ? ApiPathConstants.STORAGE : ApiPathConstants.STORAGE + "/" + normalized;
    }

    public Path resolvePublicUrl(String publicUrl) {
        String normalized = publicUrl == null ? "" : publicUrl.trim().replace('\\', '/');
        if (ApiPathConstants.STORAGE.equals(normalized)) {
            return resolveRootDir();
        }
        String prefix = ApiPathConstants.STORAGE + "/";
        if (!normalized.startsWith(prefix)) {
            return null;
        }
        String relative = normalized.substring(prefix.length());
        try {
            return resolveWithinRoot(relative);
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private Path resolveWithinRoot(String relativePath) {
        Path root = resolveRootDir();
        String normalized = relativePath == null ? "" : relativePath.trim().replace('\\', '/');
        while (normalized.startsWith("/")) {
            normalized = normalized.substring(1);
        }
        Path resolved = normalized.isBlank() ? root : root.resolve(normalized).normalize();
        if (!resolved.startsWith(root)) {
            throw new IllegalArgumentException("storage path escapes root");
        }
        return resolved;
    }
}
