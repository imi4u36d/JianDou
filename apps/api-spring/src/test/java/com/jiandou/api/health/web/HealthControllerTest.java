package com.jiandou.api.health.web;

import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.jiandou.api.health.application.RuntimeDescriptorService;
import com.jiandou.api.health.dto.RuntimeDescriptorResponse;
import org.junit.jupiter.api.Test;

class HealthControllerTest {

    @Test
    void healthDelegatesToRuntimeDescriptorService() {
        RuntimeDescriptorService service = mock(RuntimeDescriptorService.class);
        RuntimeDescriptorResponse response = new RuntimeDescriptorResponse(true, null);
        when(service.describeRuntime()).thenReturn(response);

        assertSame(response, new HealthController(service).health());
    }
}
