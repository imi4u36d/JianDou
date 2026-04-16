package com.jiandou.api.media;

import com.jiandou.api.config.JiandouStorageProperties;
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
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import javax.imageio.ImageIO;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * 本地媒体产物服务。
 */
@Service
public class LocalMediaArtifactService {

    private final JiandouStorageProperties storageProperties;
    private final Path storageRoot;
    private final String ffmpegBin;
    private final HttpClient httpClient;

    /**
     * 创建新的本地媒体产物服务。
     */
    public LocalMediaArtifactService(
        JiandouStorageProperties storageProperties,
        @Value("${JIANDOU_FFMPEG_BIN:ffmpeg}") String ffmpegBin
    ) {
        this.storageProperties = storageProperties;
        this.storageRoot = storageProperties.resolveRootDir();
        this.ffmpegBin = ffmpegBin == null || ffmpegBin.isBlank() ? "ffmpeg" : ffmpegBin.trim();
        this.httpClient = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build();
    }

    /**
     * 处理写入文本。
     * @param relativeDir relativeDir值
     * @param fileName 文件Name值
     * @param content content值
     * @return 处理结果
     */
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

    /**
     * 处理写入提示词卡片。
     * @param relativeDir relativeDir值
     * @param fileName 文件Name值
     * @param width width值
     * @param height height值
     * @param title title值
     * @param subtitle subtitle值
     * @param bodyText body文本值
     * @return 处理结果
     */
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

    /**
     * 处理写入Silent视频。
     * @param relativeDir relativeDir值
     * @param fileName 文件Name值
     * @param width width值
     * @param height height值
     * @param durationSeconds 时长Seconds值
     * @param poster poster值
     * @return 处理结果
     */
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

    /**
     * 处理ensureDirectory。
     * @param relativeDir relativeDir值
     * @return 处理结果
     */
    private Path ensureDirectory(String relativeDir) throws IOException {
        Path dir = storageRoot.resolve(relativeDir).normalize();
        Files.createDirectories(dir);
        return dir;
    }

    /**
     * 构建PublicURL。
     * @param relativeDir relativeDir值
     * @param fileName 文件Name值
     * @return 处理结果
     */
    private String buildPublicUrl(String relativeDir, String fileName) {
        String normalizedDir = relativeDir == null ? "" : relativeDir.replace('\\', '/');
        return storageProperties.buildPublicUrl(normalizedDir + "/" + fileName);
    }

    /**
     * 处理解析Absolute路径。
     * @param publicUrl publicURL值
     * @return 处理结果
     */
    public String resolveAbsolutePath(String publicUrl) {
        Path resolved = storageProperties.resolvePublicUrl(publicUrl);
        return resolved == null ? "" : resolved.toAbsolutePath().toString();
    }

    /**
     * 处理copy产物。
     * @param sourcePublicUrl 来源PublicURL值
     * @param relativeDir relativeDir值
     * @param fileName 文件Name值
     * @return 处理结果
     */
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

    /**
     * 处理materialize产物。
     * @param sourceUrl 来源URL值
     * @param relativeDir relativeDir值
     * @param fileName 文件Name值
     * @return 处理结果
     */
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

    /**
     * 处理写入Binary。
     * @param relativeDir relativeDir值
     * @param fileName 文件Name值
     * @param data data值
     * @return 处理结果
     */
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

    /**
     * 处理concatVideos。
     * @param relativeDir relativeDir值
     * @param fileName 文件Name值
     * @param sourcePublicUrls 来源PublicUrls值
     * @return 处理结果
     */
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

    /**
     * 处理safeLine。
     * @param value 待处理的值
     * @param fallback 兜底值
     * @return 处理结果
     */
    private String safeLine(String value, String fallback) {
        String normalized = value == null ? "" : value.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }

    /**
     * 处理wrap文本。
     * @param text 文本值
     * @param maxCharsPerLine 最大CharsPerLine值
     * @return 处理结果
     */
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

    /**
     * 处理文本产物。
     * @param fileName 文件Name值
     * @param absolutePath absolute路径值
     * @param publicUrl publicURL值
     * @param sizeBytes sizeBytes值
     * @param mimeType mime类型值
     * @return 处理结果
     */
    public record TextArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes,
        String mimeType
    ) {}

    /**
     * 处理图像产物。
     * @param fileName 文件Name值
     * @param absolutePath absolute路径值
     * @param publicUrl publicURL值
     * @param sizeBytes sizeBytes值
     * @param width width值
     * @param height height值
     * @param mimeType mime类型值
     * @return 处理结果
     */
    public record ImageArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes,
        int width,
        int height,
        String mimeType
    ) {}

    /**
     * 处理视频产物。
     * @param fileName 文件Name值
     * @param absolutePath absolute路径值
     * @param publicUrl publicURL值
     * @param sizeBytes sizeBytes值
     * @param width width值
     * @param height height值
     * @param durationSeconds 时长Seconds值
     * @param hasAudio hasAudio值
     * @param mimeType mime类型值
     * @return 处理结果
     */
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

    /**
     * 处理Stored产物。
     * @param fileName 文件Name值
     * @param absolutePath absolute路径值
     * @param publicUrl publicURL值
     * @param sizeBytes sizeBytes值
     * @return 处理结果
     */
    public record StoredArtifact(
        String fileName,
        String absolutePath,
        String publicUrl,
        long sizeBytes
    ) {}
}
