package com.jiandou.api.generation.text;

import java.util.List;

public record VisionCompletionInvocation(
    String systemPrompt,
    String userPrompt,
    double temperature,
    int maxTokens,
    List<String> imageUrls,
    Integer seed
) implements TextModelInvocation {

    @Override
    public boolean vision() {
        return true;
    }
}
