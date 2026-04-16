package com.jiandou.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 任务业务默认值配置。
 */
@ConfigurationProperties(prefix = "jiandou.task.defaults")
public class JiandouTaskDefaultsProperties {

    private String sourceFileName = "text_prompt";
    private String defaultAspectRatio = "9:16";
    private int defaultDurationSeconds = 8;
    private String editingMode = "drama";
    private String introTemplate = "none";
    private String outroTemplate = "none";
    private String promptSource = "spring-default";
    private String seedanceQueryModel = "seedance-1.5-pro";

    public String getSourceFileName() {
        return sourceFileName;
    }

    public void setSourceFileName(String sourceFileName) {
        this.sourceFileName = sourceFileName == null ? "text_prompt" : sourceFileName.trim();
    }

    public String getDefaultAspectRatio() {
        return defaultAspectRatio;
    }

    public void setDefaultAspectRatio(String defaultAspectRatio) {
        this.defaultAspectRatio = defaultAspectRatio == null ? "9:16" : defaultAspectRatio.trim();
    }

    public int getDefaultDurationSeconds() {
        return defaultDurationSeconds;
    }

    public void setDefaultDurationSeconds(int defaultDurationSeconds) {
        this.defaultDurationSeconds = Math.max(1, defaultDurationSeconds);
    }

    public String getEditingMode() {
        return editingMode;
    }

    public void setEditingMode(String editingMode) {
        this.editingMode = editingMode == null ? "drama" : editingMode.trim();
    }

    public String getIntroTemplate() {
        return introTemplate;
    }

    public void setIntroTemplate(String introTemplate) {
        this.introTemplate = introTemplate == null ? "none" : introTemplate.trim();
    }

    public String getOutroTemplate() {
        return outroTemplate;
    }

    public void setOutroTemplate(String outroTemplate) {
        this.outroTemplate = outroTemplate == null ? "none" : outroTemplate.trim();
    }

    public String getPromptSource() {
        return promptSource;
    }

    public void setPromptSource(String promptSource) {
        this.promptSource = promptSource == null ? "spring-default" : promptSource.trim();
    }

    public String getSeedanceQueryModel() {
        return seedanceQueryModel;
    }

    public void setSeedanceQueryModel(String seedanceQueryModel) {
        this.seedanceQueryModel = seedanceQueryModel == null ? "seedance-1.5-pro" : seedanceQueryModel.trim();
    }
}
