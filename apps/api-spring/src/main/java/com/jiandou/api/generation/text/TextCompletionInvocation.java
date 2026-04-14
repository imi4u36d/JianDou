package com.jiandou.api.generation.text;

public record TextCompletionInvocation(
    String systemPrompt,
    String userPrompt,
    double temperature,
    int maxTokens
) implements TextModelInvocation {}
