package com.jiandou.api.media;

import java.awt.Color;
import java.awt.Font;
import java.awt.GradientPaint;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import javax.imageio.ImageIO;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class LocalMediaArtifactService {

    private final Path storageRoot;
    private final String ffmpegBin;
    private final HttpClient httpClient;

    public LocalMediaArtifactService(
        @Value("${JIANDOU_STORAGE_ROOT:../../storage}") String storageRoot,
        @Value("${JIANDOU_FFMPEG_BIN:ffmpeg}") String ffmpegBin
    ) {
        this.storageRoot = Paths.get(storageRoot).toAbsolutePath().normalize();
        this.ffmpegBin = ffmpegBin == null || ffmpegBin.isBlank() ? "ffmpeg" : ffmpegBin.trim();
        this.httpClient = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build();
    }

    public TextArtifact writeText(String relativeDir, String fileName, String content) {
        try {
            Path dir = ensureDirectory(relativeDir);
            Path output = dir.resolve(fileName);
            Files.writeString(output, content == null ? "" : content, StandardCharsets.UTF_8);
            return new TextArtifact(
                fileName,
                output.toAbsolutePath().normalize().toString(),
                buildPublicUrl(relativeDir, fileName),
                Files.size(output),
                "text/markdown"
            );
        } catch (IOException ex) {
            throw new IllegalStateException("text artifact write failed: " + ex.getMessage(), ex);
        }
    }

    public ImageArtifact writePromptCard(
        String relativeDir,
        String fileName,
        int width,
        int height,
        String title,
        String subtitle,
        String bodyText
    ) {
        try {
            Path dir = ensureDirectory(relativeDir);
            Path output = dir.resolve(fileName);
            BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
            Graphics2D graphics = image.createGraphics();
            graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            graphics.setPaint(new GradientPaint(0, 0, new Color(12, 20, 36), width, height, new Color(32, 74, 135)));
            graphics.fillRect(0, 0, width, height);

            int margin = Math.max(24, Math.min(width, height) / 20);
            int cardWidth = Math.max(180, width - margin * 2);
            graphics.setColor(new Color(255, 255, 255, 228));
            graphics.fillRoundRect(margin, margin, cardWidth, Math.max(112, height / 8), 24, 24);

            graphics.setColor(new Color(15, 23, 42));
            graphics.setFont(new Font("SansSerif", Font.BOLD, Math.max(20, Math.min(width / 18, 42))));
            graphics.drawString(safeLine(title, "MEDIA PLACEHOLDER"), margin + 24, margin + 54);

            graphics.setFont(new Font("SansSerif", Font.PLAIN, Math.max(14, Math.min(width / 34, 24))));
            graphics.drawString(safeLine(subtitle, "Spring local render"), margin + 24, margin + 90);

            graphics.setColor(new Color(241, 245, 249));
            List<String> lines = wrapText(bodyText, Math.max(18, width / 24));
            int lineHeight = Math.max(24, Math.min(height / 18, 34));
            int startY = margin + 148;
            for (int index = 0; index < Math.min(lines.size(), 8); index++) {
                graphics.drawString(lines.get(index), margin + 24, startY + index * lineHeight);
            }
            graphics.dispose();
            ImageIO.write(image, "png", output.toFile());
            return new ImageArtifact(
                fileName,
                output.toAbsolutePath().normalize().toString(),
                buildPublicUrl(relativeDir, fileName),
                Files.size(output),
                width,
                height,
                "image/png"
            );
        } catch (IOException ex) {
            throw new IllegalStateException("image artifact write failed: " + ex.getMessage(), ex);
        }
    }

    public VideoArtifact writeSilentVideo(
        String relativeDir,
        String fileName,
        int width,
        int height,
        int durationSeconds,
        ImageArtifact poster
    ) {
        try {
            Path dir = ensureDirectory(relativeDir);
            Path output = dir.resolve(fileName);
            List<String> command = new ArrayList<>();
            command.add(ffmpegBin);
            command.add("-y");
            command.add("-loop");
            command.add("1");
            command.add("-i");
            command.add(poster.absolutePath());
            command.add("-f");
            command.add("lavfi");
            command.add("-i");
            command.add("anullsrc=channel_layout=stereo:sample_rate=48000");
            command.add("-t");
            command.add(String.valueOf(Math.max(1, durationSeconds)));
            command.add("-vf");
            command.add("scale=" + width + ":" + height + ",format=yuv420p");
            command.add("-r");
            command.add("24");
            command.add("-shortest");
            command.add("-c:v");
            command.add("libx264");
            command.add("-preset");
            command.add("veryfast");
            command.add("-pix_fmt");
            command.add("yuv420p");
            command.add("-c:a");
            command.add("aac");
            command.add("-b:a");
            command.add("128k");
            command.add("-movflags");
            command.add("+faststart");
            command.add(output.toString());
            Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
            int exitCode = process.waitFor();
            String processOutput = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            if (exitCode != 0 || !Files.exists(output)) {
                throw new IOException(processOutput.isBlank() ? "ffmpeg failed" : processOutput);
            }
            return new VideoArtifact(
                fileName,
                output.toAbsolutePath().normalize().toString(),
                buildPublicUrl(relativeDir, fileName),
                Files.size(output),
                width,
                height,
                Math.max(1, durationSeconds),
                true,
                "video/mp4"
            );
        } catch (Exception ex) {
            throw new IllegalStateException("video artifact write failed: " + ex.getMessage(), ex);
        }
    }

    private Path ensureDirectory(String relativeDir) throws IOException {
        Path dir = storageRoot.resolve(relativeDir).normalize();
        Files.createDirectories(dir);
        return dir;
    }

    private String buildPublicUrl(String relativeDir, String fileName) {
        String normalizedDir = relativeDir.replace('\\', '/');
        return "/storage/" + normalizedDir + "/" + fileName;
    }

    public String resolveAbsolutePath(String publicUrl) {
        String normalized = publicUrl == null ? "" : publicUrl.trim();
        if (!normalized.startsWith("/storage/")) {
            return "";
        }
        String relative = normalized.substring("/storage/".length());
        return storageRoot.resolve(relative).normalize().toAbsolutePath().toString();
    }

    public StoredArtifact copyArtifact(String sourcePublicUrl, String relativeDir, String fileName) {
        String absoluteSourcePath = resolveAbsolutePath(sourcePublicUrl);
        if (absoluteSourcePath.isBlank()) {
            throw new IllegalArgumentException("source public url is not a local storage path");
        }
        try {
            Path source = Path.of(absoluteSourcePath).toAbsolutePath().normalize();
            if (!Files.exists(source)) {
                throw new IOException("source artifact does not exist");
            }
            Path dir = ensureDirectory(relativeDir);
            Path target = dir.resolve(fileName).toAbsolutePath().normalize();
            if (!source.equals(target)) {
                Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
            }
            return new StoredArtifact(
                fileName,
                target.toString(),
                buildPublicUrl(relativeDir, fileName),
                Files.size(target)
            );
        } catch (IOException ex) {
            throw new IllegalStateException("artifact copy failed: " + ex.getMessage(), ex);
        }
    }

    public StoredArtifact materializeArtifact(String sourceUrl, String relativeDir, String fileName) {
        String absoluteSourcePath = resolveAbsolutePath(sourceUrl);
        if (!absoluteSourcePath.isBlank()) {
            return copyArtifact(sourceUrl, relativeDir, fileName);
        }
        String normalizedSourceUrl = sourceUrl == null ? "" : sourceUrl.trim();
        if (normalizedSourceUrl.isBlank()) {
            throw new IllegalArgumentException("source url is required");
        }
        try {
            Path dir = ensureDirectory(relativeDir);
            Path target = dir.resolve(fileName).toAbsolutePath().normalize();
            HttpRequest request = HttpRequest.newBuilder(URI.create(normalizedSourceUrl)).GET().build();
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new IOException("download failed with status " + response.statusCode());
            }
            Files.write(target, response.body());
            return new StoredArtifact(
                fileName,
                target.toString(),
                buildPublicUrl(relativeDir, fileName),
                Files.size(target)
            );
        } catch (Exception ex) {
            throw new IllegalStateException("artifact materialize failed: " + ex.getMessage(), ex);
        }
    }

    public StoredArtifact writeBinary(String relativeDir, String fileName, byte[] data) {
        try {
            Path dir = ensureDirectory(relativeDir);
            Path target = dir.resolve(fileName).toAbsolutePath().normalize();
            Files.write(target, data == null ? new byte[0] : data);
            return new StoredArtifact(
                fileName,
                target.toString(),
                buildPublicUrl(relativeDir, fileName),
                Files.size(target)
            );
        } catch (IOException ex) {
            throw new IllegalStateException("artifact binary write failed: " + ex.getMessage(), ex);
        }
    }

    public StoredArtifact concatVideos(String relativeDir, String fileName, List<String> sourcePublicUrls) {
        if (sourcePublicUrls == null || sourcePublicUrls.size() < 2) {
            throw new IllegalArgumentException("at least two source videos are required");
        }
        try {
            List<Path> sourcePaths = new ArrayList<>();
            for (String sourcePublicUrl : sourcePublicUrls) {
                String absoluteSourcePath = resolveAbsolutePath(sourcePublicUrl);
                if (absoluteSourcePath.isBlank()) {
                    throw new IllegalArgumentException("source public url is not a local storage path");
                }
                Path source = Path.of(absoluteSourcePath).toAbsolutePath().normalize();
                if (!Files.exists(source)) {
                    throw new IOException("source video does not exist");
                }
                sourcePaths.add(source);
            }
            Path dir = ensureDirectory(relativeDir);
            Path output = dir.resolve(fileName).toAbsolutePath().normalize();
            Path listFile = Files.createTempFile("jiandou-join-", ".txt");
            try {
                List<String> lines = new ArrayList<>();
                for (Path sourcePath : sourcePaths) {
                    lines.add("file '" + sourcePath.toString().replace("'", "'\\''") + "'");
                }
                Files.write(listFile, lines, StandardCharsets.UTF_8);
                List<String> command = new ArrayList<>();
                command.add(ffmpegBin);
                command.add("-y");
                command.add("-f");
                command.add("concat");
                command.add("-safe");
                command.add("0");
                command.add("-i");
                command.add(listFile.toString());
                command.add("-c");
                command.add("copy");
                command.add("-movflags");
                command.add("+faststart");
                command.add(output.toString());
                Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
                int exitCode = process.waitFor();
                String processOutput = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
                if (exitCode != 0 || !Files.exists(output)) {
                    throw new IOException(processOutput.isBlank() ? "ffmpeg concat failed" : processOutput);
                }
                return new StoredArtifact(
                    fileName,
                    output.toString(),
                    buildPublicUrl(relativeDir, fileName),
                    Files.size(output)
                );
            } finally {
                Files.deleteIfExists(listFile);
            }
        } catch (Exception ex) {
            throw new IllegalStateException("video concat failed: " + ex.getMessage(), ex);
        }
    }

    private String safeLine(String value, String fallback) {
        String normalized = value == null ? "" : value.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }

    private List<String> wrapText(String text, int maxCharsPerLine) {
        String normalized = text == null ? "" : text.replace('\n', ' ').trim();
        if (normalized.isBlank()) {
            return List.of("placeholder output");
        }
        List<String> lines = new ArrayList<>();
        int cursor = 0;
        while (cursor < normalized.length()) {
            int end = Math.min(normalized.length(), cursor + Math.max(12, maxCharsPerLine));
            lines.add(normalized.substring(cursor, end));
            cursor = end;
        }
        return lines;
    }

    public record TextArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes,
        String mimeType
    ) {}

    public record ImageArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes,
        int width,
        int height,
        String mimeType
    ) {}

    public record VideoArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes,
        int width,
        int height,
        int durationSeconds,
        boolean hasAudio,
        String mimeType
    ) {}

    public record StoredArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes
    ) {}
}
