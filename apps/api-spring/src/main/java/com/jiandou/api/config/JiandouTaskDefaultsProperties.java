package com.jiandou.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 任务业务默认值配置。
 */
@ConfigurationProperties(prefix = "jiandou.task.defaults")
public class JiandouTaskDefaultsProperties {

    private String sourceFileName = JiandouTaskDefaultValues.SOURCE_FILE_NAME;
    private String defaultAspectRatio = JiandouTaskDefaultValues.DEFAULT_ASPECT_RATIO;
    private int defaultDurationSeconds = JiandouTaskDefaultValues.DEFAULT_DURATION_SECONDS;
    private String editingMode = JiandouTaskDefaultValues.EDITING_MODE;
    private String introTemplate = JiandouTaskDefaultValues.INTRO_TEMPLATE;
    private String outroTemplate = JiandouTaskDefaultValues.OUTRO_TEMPLATE;
    private String promptSource = JiandouTaskDefaultValues.PROMPT_SOURCE;
    private String seedanceQueryModel = JiandouTaskDefaultValues.SEEDANCE_QUERY_MODEL;

    public String getSourceFileName() {
        return sourceFileName;
    }

    public void setSourceFileName(String sourceFileName) {
        this.sourceFileName = sourceFileName == null ? JiandouTaskDefaultValues.SOURCE_FILE_NAME : sourceFileName.trim();
    }

    public String getDefaultAspectRatio() {
        return defaultAspectRatio;
    }

    public void setDefaultAspectRatio(String defaultAspectRatio) {
        this.defaultAspectRatio = defaultAspectRatio == null ? JiandouTaskDefaultValues.DEFAULT_ASPECT_RATIO : defaultAspectRatio.trim();
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
        this.editingMode = editingMode == null ? JiandouTaskDefaultValues.EDITING_MODE : editingMode.trim();
    }

    public String getIntroTemplate() {
        return introTemplate;
    }

    public void setIntroTemplate(String introTemplate) {
        this.introTemplate = introTemplate == null ? JiandouTaskDefaultValues.INTRO_TEMPLATE : introTemplate.trim();
    }

    public String getOutroTemplate() {
        return outroTemplate;
    }

    public void setOutroTemplate(String outroTemplate) {
        this.outroTemplate = outroTemplate == null ? JiandouTaskDefaultValues.OUTRO_TEMPLATE : outroTemplate.trim();
    }

    public String getPromptSource() {
        return promptSource;
    }

    public void setPromptSource(String promptSource) {
        this.promptSource = promptSource == null ? JiandouTaskDefaultValues.PROMPT_SOURCE : promptSource.trim();
    }

    public String getSeedanceQueryModel() {
        return seedanceQueryModel;
    }

    public void setSeedanceQueryModel(String seedanceQueryModel) {
        this.seedanceQueryModel = seedanceQueryModel == null ? JiandouTaskDefaultValues.SEEDANCE_QUERY_MODEL : seedanceQueryModel.trim();
    }
}
