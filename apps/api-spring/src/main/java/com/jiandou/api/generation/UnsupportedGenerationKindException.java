package com.jiandou.api.generation;

public final class UnsupportedGenerationKindException extends RuntimeException {

    public UnsupportedGenerationKindException(String kind) {
        super("unsupported generation kind: " + kind);
    }
}
