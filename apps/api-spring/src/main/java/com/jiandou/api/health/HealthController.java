package com.jiandou.api.health;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v2")
public class HealthController {

    private final RuntimeDescriptorService runtimeDescriptorService;

    public HealthController(RuntimeDescriptorService runtimeDescriptorService) {
        this.runtimeDescriptorService = runtimeDescriptorService;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return runtimeDescriptorService.describeRuntime();
    }
}
