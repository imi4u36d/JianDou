package com.jiandou.api.task.application.port;

import java.util.List;

public interface TaskQueuePort {

    void enqueue(String taskId);

    void remove(String taskId);

    String claimNext(String workerInstanceId);

    List<String> snapshot();
}
