package com.jiandou.api.generation.exception;

/**
 * Unsupported生成类型异常。
 */
public final class UnsupportedGenerationKindException extends RuntimeException {

    /**
     * 创建新的Unsupported生成类型异常。
     * @param kind 类型值
     */
    public UnsupportedGenerationKindException(String kind) {
        super("unsupported generation kind: " + kind);
    }
}
