package com.jiandou.api.generation.exception;

/**
 * 生成Provider异常。
 */
public final class GenerationProviderException extends RuntimeException {

    /**
     * 创建新的生成Provider异常。
     * @param message 消息文本
     */
    public GenerationProviderException(String message) {
        super(message);
    }
}
