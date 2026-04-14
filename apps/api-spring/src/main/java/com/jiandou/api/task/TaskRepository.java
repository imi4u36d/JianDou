package com.jiandou.api.task;

import com.jiandou.api.task.application.port.TaskPersistencePort;
import java.util.Collection;

public interface TaskRepository extends TaskPersistencePort {
    @Override
    Collection<TaskRecord> findAll();
}
