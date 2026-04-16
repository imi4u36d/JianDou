package com.jiandou.api.generation.image;

import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import com.jiandou.api.generation.runtime.MediaProviderCapabilities;
import com.jiandou.api.generation.runtime.MediaProviderConfig;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import java.util.List;
import org.junit.jupiter.api.Test;

class ImageModelProviderRegistryTest {

    @Test
    void resolveReturnsSeedreamProviderForSeedreamProfile() {
        ImageModelProviderRegistry registry = new ImageModelProviderRegistry(List.of(
            new SeedreamImageModelProvider(new ImageProviderTransport(new com.fasterxml.jackson.databind.ObjectMapper()))
        ));

        ImageModelProvider provider = registry.resolve(profile("seedream"));

        assertInstanceOf(SeedreamImageModelProvider.class, provider);
    }

    private MediaProviderProfile profile(String provider) {
        return new MediaProviderProfile(
            new MediaProviderConfig(
                "image",
                provider + "-model",
                provider,
                provider + "-model",
                "k",
                "https://api.example.com",
                "",
                60,
                "test"
            ),
            new MediaProviderCapabilities(false, false, false, false, 5, 120, "", List.of(), List.of())
        );
    }
}
