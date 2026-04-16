package com.jiandou.api.task.infrastructure;

import com.jiandou.api.task.application.port.TaskQueuePort;
import com.jiandou.api.task.persistence.TaskRepository;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * 任务队列协调器。
 */
@Component
public class TaskQueueCoordinator implements TaskQueuePort {

    private static final int SNAPSHOT_LIMIT = 500;

    private final TaskRepository taskRepository;

    /**
     * 创建新的任务队列协调器。
     * @param taskRepository 任务仓储值
     */
    public TaskQueueCoordinator(TaskRepository taskRepository) {
        this.taskRepository = taskRepository;
    }

    /**
     * 将enqueue加入队列。
     * @param taskId 任务标识
     */
    @Override
    public void enqueue(String taskId) {
        // 队列状态由已持久化的尝试记录推导，不在这里维护内存态。
    }

    /**
     * 移除remove。
     * @param taskId 任务标识
     */
    @Override
    public void remove(String taskId) {
        taskRepository.removeQueuedTask(taskId);
    }

    /**
     * 领取Next。
     * @param workerInstanceId 工作节点实例标识
     * @return 处理结果
     */
    @Override
    public String claimNext(String workerInstanceId) {
        return taskRepository.claimNextQueuedTask(workerInstanceId);
    }

    /**
     * 处理快照。
     * @return 处理结果
     */
    @Override
    public List<String> snapshot() {
        return taskRepository.listQueuedTaskIds(SNAPSHOT_LIMIT);
    }
}
