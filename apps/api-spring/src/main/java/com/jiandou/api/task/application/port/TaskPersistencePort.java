package com.jiandou.api.task.application.port;

import com.jiandou.api.task.TaskRecord;
import com.jiandou.api.task.persistence.TaskPersistenceMutation;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.List;
import java.util.Map;

/**
 * 任务持久化端口定义。
 */
public interface TaskPersistencePort {

    /**
     * 保存save。
     * @param task 要处理的任务对象
     */
    void save(TaskRecord task);

    /**
     * 保存变更。
     * @param mutation 变更值
     */
    void saveMutation(TaskPersistenceMutation mutation);

    /**
     * 查找工作节点Instance。
     * @param workerInstanceId 工作节点实例标识
     * @return 处理结果
     */
    Map<String, Object> findWorkerInstance(String workerInstanceId);

    /**
     * 列出工作节点Instances。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> listWorkerInstances(int limit);

    /**
     * 移除Queued任务。
     * @param taskId 任务标识
     */
    void removeQueuedTask(String taskId);

    /**
     * 领取NextQueued任务。
     * @param workerInstanceId 工作节点实例标识
     * @return 处理结果
     */
    String claimNextQueuedTask(String workerInstanceId);

    /**
     * 列出Queued任务标识列表。
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<String> listQueuedTaskIds(int limit);

    /**
     * 列出StaleRunningClaims。
     * @param staleBefore staleBefore值
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> listStaleRunningClaims(OffsetDateTime staleBefore, int limit);

    /**
     * 列出Stale工作节点Instance标识列表。
     * @param staleBefore staleBefore值
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<String> listStaleWorkerInstanceIds(OffsetDateTime staleBefore, int limit);

    /**
     * 列出队列Events。
     * @param taskId 任务标识
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> listQueueEvents(String taskId, int limit);

    /**
     * 列出Traces。
     * @param taskId 任务标识
     * @param stage 阶段名称
     * @param level level值
     * @param query 查询值
     * @param limit 返回的最大条目数
     * @return 处理结果
     */
    List<Map<String, Object>> listTraces(String taskId, String stage, String level, String query, int limit);

    /**
     * 查找By标识。
     * @param taskId 任务标识
     * @return 处理结果
     */
    TaskRecord findById(String taskId);

    /**
     * 查找All。
     * @return 处理结果
     */
    Collection<TaskRecord> findAll();

    /**
     * 删除删除。
     * @param taskId 任务标识
     */
    void delete(String taskId);
}
