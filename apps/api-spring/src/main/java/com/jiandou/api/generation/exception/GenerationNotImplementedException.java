package com.jiandou.api.generation.exception;

/**
 * 生成NotImplemented异常。
 */
public final class GenerationNotImplementedException extends RuntimeException {

    /**
     * 创建新的生成NotImplemented异常。
     * @param message 消息文本
     */
    public GenerationNotImplementedException(String message) {
        super(message);
    }
}
