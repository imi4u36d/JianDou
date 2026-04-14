package com.jiandou.api.generation;

public final class GenerationRunNotFoundException extends RuntimeException {

    public GenerationRunNotFoundException(String runId) {
        super("generation run not found: " + runId);
    }
}
