package com.jiandou.api.generation.video;

import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiandou.api.generation.runtime.MediaProviderCapabilities;
import com.jiandou.api.generation.runtime.MediaProviderConfig;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import java.util.List;
import org.junit.jupiter.api.Test;

class VideoModelProviderRegistryTest {

    @Test
    void resolveReturnsSeedanceProviderForSeedanceProfile() {
        VideoProviderTransport videoProviderTransport = new VideoProviderTransport(new ObjectMapper());
        VideoModelProviderRegistry registry = new VideoModelProviderRegistry(List.of(
            new SeedanceVideoModelProvider(videoProviderTransport)
        ));

        VideoModelProvider provider = registry.resolve(profile("seedance"));

        assertInstanceOf(SeedanceVideoModelProvider.class, provider);
    }

    private MediaProviderProfile profile(String provider) {
        return new MediaProviderProfile(
            new MediaProviderConfig(
                "video",
                provider + "-model",
                provider,
                provider + "-model",
                "k",
                "https://api.example.com",
                "https://api.example.com/tasks",
                60,
                "test"
            ),
            new MediaProviderCapabilities(false, true, false, false, 1, 30, "i2v", List.of(), List.of(), false)
        );
    }
}
