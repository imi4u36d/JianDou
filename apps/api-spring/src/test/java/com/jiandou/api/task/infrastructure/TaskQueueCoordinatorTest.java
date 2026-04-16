package com.jiandou.api.task.infrastructure;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.jiandou.api.task.persistence.TaskRepository;
import java.util.List;
import org.junit.jupiter.api.Test;

class TaskQueueCoordinatorTest {

    @Test
    void enqueueIsNoOp() {
        TaskRepository repository = mock(TaskRepository.class);
        TaskQueueCoordinator coordinator = new TaskQueueCoordinator(repository);

        assertDoesNotThrow(() -> coordinator.enqueue("task_1"));
        verifyNoInteractions(repository);
    }

    @Test
    void removeAndClaimDelegateToRepository() {
        TaskRepository repository = mock(TaskRepository.class);
        TaskQueueCoordinator coordinator = new TaskQueueCoordinator(repository);

        when(repository.claimNextQueuedTask("worker_1")).thenReturn("task_2");

        coordinator.remove("task_1");
        assertEquals("task_2", coordinator.claimNext("worker_1"));

        verify(repository).removeQueuedTask("task_1");
        verify(repository).claimNextQueuedTask("worker_1");
    }

    @Test
    void snapshotUsesFixedLimit() {
        TaskRepository repository = mock(TaskRepository.class);
        TaskQueueCoordinator coordinator = new TaskQueueCoordinator(repository);

        when(repository.listQueuedTaskIds(500)).thenReturn(List.of("task_1", "task_2"));

        assertEquals(List.of("task_1", "task_2"), coordinator.snapshot());
        verify(repository).listQueuedTaskIds(500);
    }
}
