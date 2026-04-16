package com.jiandou.api.generation.video;

import com.jiandou.api.generation.runtime.MediaProviderProfile;
import com.jiandou.api.generation.RemoteTaskQueryResult;
import com.jiandou.api.generation.RemoteVideoTaskSubmission;

/**
 * 视频模型 provider SPI。
 */
public interface VideoModelProvider {

    /**
     * 检查是否支持当前 profile。
     * @param profile 媒体配置值
     * @return 是否满足条件
     */
    boolean supports(MediaProviderProfile profile);

    /**
     * 提交视频生成任务。
     * @param profile 媒体配置值
     * @param request 请求值
     * @return 处理结果
     */
    RemoteVideoTaskSubmission submit(MediaProviderProfile profile, VideoGenerationRequest request);

    /**
     * 查询远程视频任务。
     * @param profile 媒体配置值
     * @param remoteTaskId 远程任务标识
     * @return 处理结果
     */
    RemoteTaskQueryResult query(MediaProviderProfile profile, String remoteTaskId);
}
