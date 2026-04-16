package com.jiandou.api.config;

import com.jiandou.api.task.domain.ExecutionMode;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * JianDou 运行时应用配置。
 */
@ConfigurationProperties(prefix = "jiandou.app")
public class JiandouAppProperties {

    private String env = "dev";
    private String executionMode = "queue";
    private String webOrigin = "http://127.0.0.1:5173,http://localhost:5173";

    public String getEnv() {
        return env;
    }

    public void setEnv(String env) {
        this.env = env == null ? "dev" : env.trim();
    }

    public String getExecutionMode() {
        return executionMode;
    }

    public ExecutionMode getExecutionModeEnum() {
        return ExecutionMode.from(executionMode);
    }

    public void setExecutionMode(String executionMode) {
        this.executionMode = executionMode == null ? ExecutionMode.QUEUE.value() : ExecutionMode.normalize(executionMode);
    }

    public String getWebOrigin() {
        return webOrigin;
    }

    public void setWebOrigin(String webOrigin) {
        this.webOrigin = webOrigin == null ? "" : webOrigin.trim();
    }
}
