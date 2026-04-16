package com.jiandou.api.task.persistence;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.application.port.TaskPersistencePort;
import java.util.Collection;

/**
 * 任务仓储契约。
 */
public interface TaskRepository extends TaskPersistencePort {
    /**
     * 查找All。
     * @return 处理结果
     */
    @Override
    Collection<TaskRecord> findAll();
}
