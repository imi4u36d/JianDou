package com.jiandou.api.generation.text;

import java.util.List;

public sealed interface TextModelInvocation permits TextCompletionInvocation, VisionCompletionInvocation {

    String systemPrompt();

    String userPrompt();

    double temperature();

    int maxTokens();

    default boolean vision() {
        return false;
    }

    default List<String> imageUrls() {
        return List.of();
    }

    default Integer seed() {
        return null;
    }
}
