package com.jiandou.api.task.application.port;

import com.jiandou.api.task.persistence.TaskAttemptRow;
import com.jiandou.api.task.persistence.TaskRow;
import com.jiandou.api.task.persistence.TaskStageRunRow;
import com.jiandou.api.task.persistence.TaskStatusHistoryRow;
import java.util.List;

public interface TaskAggregateQueryPort {

    TaskRow loadTask(String taskId);

    List<TaskRow> listTasks(String query, String status);

    List<TaskAttemptRow> listAttempts(String taskId, int limit);

    List<TaskStageRunRow> listStageRuns(String taskId, int limit);

    List<TaskStatusHistoryRow> listStatusHistory(String taskId, int limit);
}
