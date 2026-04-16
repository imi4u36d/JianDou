package com.jiandou.api.task.runtime;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.domain.TaskResultTypes;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskWorkerJoinStageServiceTest {

    @Test
    void scheduleJoinIgnoresInvalidOrInsufficientTasks() {
        JoinOutputService joinOutputService = mock(JoinOutputService.class);
        TaskWorkerJoinStageService service = new TaskWorkerJoinStageService(joinOutputService);
        TaskRecord blankIdTask = new TaskRecord();
        blankIdTask.setId(" ");
        TaskRecord singleClipTask = new TaskRecord();
        singleClipTask.setId("task_1");
        singleClipTask.addOutput(Map.of("resultType", TaskResultTypes.VIDEO, "clipIndex", 1));

        service.scheduleJoin(null);
        service.scheduleJoin(blankIdTask);
        service.scheduleJoin(singleClipTask);

        verify(joinOutputService, never()).scheduleJoin(org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.anyInt());
    }

    @Test
    void scheduleJoinUsesMaxPrimaryVideoClipIndex() {
        JoinOutputService joinOutputService = mock(JoinOutputService.class);
        TaskWorkerJoinStageService service = new TaskWorkerJoinStageService(joinOutputService);
        TaskRecord task = new TaskRecord();
        task.setId("task_join");
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO, "clipIndex", "2"));
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO, "clipIndex", 4));
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO_CLIP, "clipIndex", 9));
        task.addOutput(Map.of("resultType", TaskResultTypes.VIDEO_JOIN, "clipIndex", 12));

        service.scheduleJoin(task);

        verify(joinOutputService).scheduleJoin("task_join", 4);
    }
}
