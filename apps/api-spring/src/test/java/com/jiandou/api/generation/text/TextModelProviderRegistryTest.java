package com.jiandou.api.generation.text;

import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import org.junit.jupiter.api.Test;

class TextModelProviderRegistryTest {

    @Test
    void resolveReturnsCompatibleProviderForConfiguredTextProfile() {
        TextModelProviderRegistry registry = new TextModelProviderRegistry(java.util.List.of(
            new OpenAiCompatibleTextModelProvider(
                new TextProviderTransport(new ObjectMapper()),
                java.util.List.of(
                    new ResponsesApiInvocationStrategy(),
                    new ChatCompletionsInvocationStrategy()
                )
            )
        ));

        TextModelProvider provider = registry.resolve(profile());

        assertInstanceOf(OpenAiCompatibleTextModelProvider.class, provider);
    }

    private ModelRuntimeProfile profile() {
        return new ModelRuntimeProfile(
            new com.jiandou.api.generation.runtime.TextProviderConfig(
                "text",
                "qwen-plus",
                "qwen",
                "qwen-plus",
                "",
                "k",
                "https://api.example.com/v1",
                60,
                0.2,
                2048,
                "test"
            ),
            new com.jiandou.api.generation.runtime.TextProviderCapabilities(false, true, false)
        );
    }
}
