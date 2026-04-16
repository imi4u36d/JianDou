package com.jiandou.api.generation.exception;

/**
 * 生成运行NotFound异常。
 */
public final class GenerationRunNotFoundException extends RuntimeException {

    /**
     * 创建新的生成运行NotFound异常。
     * @param runId 运行标识值
     */
    public GenerationRunNotFoundException(String runId) {
        super("generation run not found: " + runId);
    }
}
