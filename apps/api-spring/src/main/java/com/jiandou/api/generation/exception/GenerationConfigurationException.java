package com.jiandou.api.generation.exception;

/**
 * 生成配置异常。
 */
public final class GenerationConfigurationException extends RuntimeException {

    /**
     * 创建新的生成配置异常。
     * @param message 消息文本
     */
    public GenerationConfigurationException(String message) {
        super(message);
    }
}
