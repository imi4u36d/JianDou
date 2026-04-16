package com.jiandou.api.generation.web;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.config.JiandouTaskOpsProperties;
import com.jiandou.api.generation.application.GenerationApplicationService;
import com.jiandou.api.generation.exception.GenerationConfigurationException;
import com.jiandou.api.generation.exception.GenerationNotImplementedException;
import com.jiandou.api.generation.exception.GenerationProviderException;
import com.jiandou.api.generation.exception.GenerationRunNotFoundException;
import com.jiandou.api.generation.exception.UnsupportedGenerationKindException;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class GenerationControllerTest {

    private GenerationApplicationService service;
    private GenerationController controller;

    @BeforeEach
    void setUp() {
        service = mock(GenerationApplicationService.class);
        JiandouTaskOpsProperties taskOpsProperties = new JiandouTaskOpsProperties();
        taskOpsProperties.setGenerationRunListLimit(12);
        controller = new GenerationController(service, taskOpsProperties);
    }

    @Test
    void catalogListRunsAndUsageDelegate() {
        Map<String, Object> catalog = Map.of("catalog", true);
        List<Map<String, Object>> runs = List.of(Map.of("id", "run_1"));
        Map<String, Object> usage = Map.of("items", List.of());
        when(service.catalog()).thenReturn(catalog);
        when(service.listRuns(12)).thenReturn(runs);
        when(service.usage()).thenReturn(usage);

        assertSame(catalog, controller.catalog());
        assertSame(runs, controller.listRuns());
        assertSame(usage, controller.usage());
        verify(service).listRuns(12);
    }

    @Test
    void createRunPassesThroughSuccess() {
        Map<String, Object> request = Map.of("kind", "probe");
        Map<String, Object> response = Map.of("id", "run_1");
        when(service.createRun(request)).thenReturn(response);

        assertSame(response, controller.createRun(request));
    }

    @Test
    void createRunMapsBadRequestErrors() {
        when(service.createRun(Map.of("kind", "x"))).thenThrow(new UnsupportedGenerationKindException("x"));

        ResponseStatusException ex = assertThrows(ResponseStatusException.class, () -> controller.createRun(Map.of("kind", "x")));

        assertEquals(HttpStatus.BAD_REQUEST, ex.getStatusCode());
    }

    @Test
    void createRunMapsServiceAvailabilityGatewayAndNotImplementedErrors() {
        when(service.createRun(Map.of("kind", "cfg"))).thenThrow(new GenerationConfigurationException("cfg"));
        when(service.createRun(Map.of("kind", "provider"))).thenThrow(new GenerationProviderException("provider"));
        when(service.createRun(Map.of("kind", "todo"))).thenThrow(new GenerationNotImplementedException("todo"));

        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, assertThrows(ResponseStatusException.class, () -> controller.createRun(Map.of("kind", "cfg"))).getStatusCode());
        assertEquals(HttpStatus.BAD_GATEWAY, assertThrows(ResponseStatusException.class, () -> controller.createRun(Map.of("kind", "provider"))).getStatusCode());
        assertEquals(HttpStatus.NOT_IMPLEMENTED, assertThrows(ResponseStatusException.class, () -> controller.createRun(Map.of("kind", "todo"))).getStatusCode());
    }

    @Test
    void getRunMapsNotFound() {
        when(service.getRun("missing")).thenThrow(new GenerationRunNotFoundException("missing"));

        ResponseStatusException ex = assertThrows(ResponseStatusException.class, () -> controller.getRun("missing"));

        assertEquals(HttpStatus.NOT_FOUND, ex.getStatusCode());
    }

    @Test
    void getRunPassesThroughSuccess() {
        Map<String, Object> run = Map.of("id", "run_1");
        when(service.getRun("run_1")).thenReturn(run);

        assertSame(run, controller.getRun("run_1"));
    }
}
