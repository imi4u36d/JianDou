package com.jiandou.api.task.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.jiandou.api.config.JiandouTaskDefaultsProperties;
import com.jiandou.api.generation.GenerationModelKinds;
import com.jiandou.api.generation.RemoteTaskQueryResult;
import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.runtime.ModelRuntimePropertiesResolver;
import com.jiandou.api.generation.video.VideoModelProvider;
import com.jiandou.api.generation.video.VideoModelProviderRegistry;
import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.web.dto.CreateGenerationTaskRequest;
import com.jiandou.api.task.web.dto.GenerateCreativePromptRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskApplicationServiceImplTest {

    @Test
    void createGenerationTaskReturnsQueriedTaskView() {
        TaskQueryService queryService = mock(TaskQueryService.class);
        TaskCommandService commandService = mock(TaskCommandService.class);
        ModelRuntimePropertiesResolver modelResolver = mock(ModelRuntimePropertiesResolver.class);
        VideoModelProviderRegistry videoModelProviderRegistry = mock(VideoModelProviderRegistry.class);
        TaskApplicationServiceImpl service = new TaskApplicationServiceImpl(
            queryService,
            commandService,
            modelResolver,
            videoModelProviderRegistry,
            defaultsProperties()
        );
        CreateGenerationTaskRequest request = new CreateGenerationTaskRequest(
            "title",
            "prompt",
            "9:16",
            "text-model",
            "vision-model",
            "image-model",
            "video-model",
            "720p",
            7,
            5,
            1,
            5,
            5,
            "transcript",
            false
        );
        TaskRecord task = new TaskRecord();
        task.setId("task_123");
        Map<String, Object> detail = Map.of("id", "task_123", "status", "PENDING");

        when(commandService.createGenerationTask(request)).thenReturn(task);
        when(queryService.getTask("task_123")).thenReturn(detail);

        assertEquals(detail, service.createGenerationTask(request));
        verify(commandService).createGenerationTask(request);
        verify(queryService).getTask("task_123");
    }

    @Test
    void generateCreativePromptTrimsTitleAndUsesFallback() {
        TaskApplicationServiceImpl service = new TaskApplicationServiceImpl(
            mock(TaskQueryService.class),
            mock(TaskCommandService.class),
            mock(ModelRuntimePropertiesResolver.class),
            mock(VideoModelProviderRegistry.class),
            defaultsProperties()
        );

        Map<String, Object> trimmed = service.generateCreativePrompt(
            new GenerateCreativePromptRequest("  城市场景  ", null, null, null, null, null, null)
        );
        Map<String, Object> fallback = service.generateCreativePrompt(
            new GenerateCreativePromptRequest("   ", null, null, null, null, null, null)
        );

        assertTrue(String.valueOf(trimmed.get("prompt")).endsWith("城市场景"));
        assertTrue(String.valueOf(fallback.get("prompt")).endsWith("未命名任务"));
        assertEquals("catalog", trimmed.get("source"));
    }

    @Test
    void getSeedanceTaskResultNormalizesBlankValues() {
        TaskQueryService queryService = mock(TaskQueryService.class);
        TaskCommandService commandService = mock(TaskCommandService.class);
        ModelRuntimePropertiesResolver modelResolver = mock(ModelRuntimePropertiesResolver.class);
        VideoModelProviderRegistry videoModelProviderRegistry = mock(VideoModelProviderRegistry.class);
        TaskApplicationServiceImpl service = new TaskApplicationServiceImpl(
            queryService,
            commandService,
            modelResolver,
            videoModelProviderRegistry,
            defaultsProperties()
        );
        MediaProviderProfile profile = new MediaProviderProfile(
            "seedance",
            "seedance-query-v1",
            "secret",
            "https://video.example.com",
            "https://task.example.com",
            120,
            5,
            300,
            false,
            false,
            false,
            "yaml"
        );
        VideoModelProvider provider = mock(VideoModelProvider.class);

        when(modelResolver.resolveVideoProfile("seedance-query-v1")).thenReturn(profile);
        when(videoModelProviderRegistry.resolve(profile)).thenReturn(provider);
        when(provider.query(profile, "remote-task-1")).thenReturn(
            new RemoteTaskQueryResult("remote-task-1", "SUCCEEDED", "   ", " ", Map.of("providerStatus", "done"))
        );

        Map<String, Object> result = service.getSeedanceTaskResult("remote-task-1");

        assertEquals("remote-task-1", result.get("taskId"));
        assertEquals("SUCCEEDED", result.get("status"));
        assertNull(result.get("videoUrl"));
        assertNull(result.get("message"));
        assertEquals(Map.of("providerStatus", "done"), result.get("payload"));
    }

    @Test
    void adminOverviewReflectsModelReadiness() {
        TaskQueryService queryService = mock(TaskQueryService.class);
        TaskCommandService commandService = mock(TaskCommandService.class);
        ModelRuntimePropertiesResolver modelResolver = mock(ModelRuntimePropertiesResolver.class);
        VideoModelProviderRegistry videoModelProviderRegistry = mock(VideoModelProviderRegistry.class);
        TaskApplicationServiceImpl service = new TaskApplicationServiceImpl(
            queryService,
            commandService,
            modelResolver,
            videoModelProviderRegistry,
            defaultsProperties()
        );
        Map<String, Object> overview = new LinkedHashMap<>();
        overview.put("counts", Map.of("totalTasks", 1));

        when(queryService.adminOverview()).thenReturn(overview);
        when(modelResolver.listModelsByKind(GenerationModelKinds.TEXT)).thenReturn(List.of(Map.of("name", "text")));
        when(modelResolver.listModelsByKind(GenerationModelKinds.VISION)).thenReturn(List.of(Map.of("name", "vision")));
        when(modelResolver.listModelsByKind(GenerationModelKinds.IMAGE)).thenReturn(List.of(Map.of("name", "image")));
        when(modelResolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of());

        Map<String, Object> notReady = service.adminOverview();

        assertFalse((Boolean) notReady.get("modelReady"));
        assertNull(notReady.get("primaryModel"));
        assertNull(notReady.get("textModel"));
        assertNull(notReady.get("visionModel"));

        when(modelResolver.listModelsByKind(GenerationModelKinds.VIDEO)).thenReturn(List.of(Map.of("name", "video")));

        Map<String, Object> ready = service.adminOverview();

        assertTrue((Boolean) ready.get("modelReady"));
    }

    private JiandouTaskDefaultsProperties defaultsProperties() {
        JiandouTaskDefaultsProperties properties = new JiandouTaskDefaultsProperties();
        properties.setPromptSource("catalog");
        properties.setSeedanceQueryModel("seedance-query-v1");
        return properties;
    }
}
