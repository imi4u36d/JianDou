package com.jiandou.api.task;

import com.jiandou.api.task.application.port.TaskQueuePort;
import java.util.List;
import org.springframework.stereotype.Component;

@Component
public class TaskQueueCoordinator implements TaskQueuePort {

    private static final int SNAPSHOT_LIMIT = 500;

    private final TaskRepository taskRepository;

    public TaskQueueCoordinator(TaskRepository taskRepository) {
        this.taskRepository = taskRepository;
    }

    @Override
    public void enqueue(String taskId) {
        // Queue state is derived from persisted attempts.
    }

    @Override
    public void remove(String taskId) {
        taskRepository.removeQueuedTask(taskId);
    }

    @Override
    public String claimNext(String workerInstanceId) {
        return taskRepository.claimNextQueuedTask(workerInstanceId);
    }

    @Override
    public List<String> snapshot() {
        return taskRepository.listQueuedTaskIds(SNAPSHOT_LIMIT);
    }
}
