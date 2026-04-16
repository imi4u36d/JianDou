package com.jiandou.api.task.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;

import com.jiandou.api.task.TaskRecord;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TaskPersistenceMutationTest {

    @Test
    void mutationTracksTaskIdAndIgnoresNullOrEmptyRows() {
        TaskRecord task = new TaskRecord();
        task.setId("task_1");
        TaskPersistenceMutation mutation = new TaskPersistenceMutation()
            .task(task)
            .taskId(" custom ")
            .addAttempt(Map.of("id", "attempt_1"))
            .addStatusHistory(Map.of())
            .addTrace(null)
            .addStageRun(Map.of("id", "stage_1"))
            .addModelCall(Map.of("id", "call_1"))
            .addMaterial(Map.of("id", "mat_1"))
            .addResult(Map.of("id", "res_1"))
            .addQueueEvent(Map.of("id", "queue_1"))
            .addWorkerInstance(Map.of("id", "worker_1"));

        assertSame(task, mutation.task());
        assertEquals("custom", mutation.taskId());
        assertEquals(1, mutation.attempts().size());
        assertEquals(0, mutation.statusHistoryRows().size());
        assertEquals(0, mutation.traceRows().size());
        assertEquals(1, mutation.stageRunRows().size());
        assertEquals(1, mutation.modelCallRows().size());
        assertEquals(1, mutation.materialRows().size());
        assertEquals(1, mutation.resultRows().size());
        assertEquals(1, mutation.queueEventRows().size());
        assertEquals(1, mutation.workerInstanceRows().size());
    }
}
