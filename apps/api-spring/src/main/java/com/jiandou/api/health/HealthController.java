package com.jiandou.api.health;

import com.jiandou.api.health.dto.RuntimeDescriptorResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 对外暴露运行时健康信息和模型目录快照。
 */
@RestController
@RequestMapping("/api/v2")
public class HealthController {

    private final RuntimeDescriptorService runtimeDescriptorService;

    public HealthController(RuntimeDescriptorService runtimeDescriptorService) {
        this.runtimeDescriptorService = runtimeDescriptorService;
    }

    @GetMapping("/health")
    public RuntimeDescriptorResponse health() {
        return runtimeDescriptorService.describeRuntime();
    }
}
