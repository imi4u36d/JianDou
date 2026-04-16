package com.jiandou.api.generation.text;

import com.jiandou.api.generation.runtime.ModelRuntimeProfile;

/**
 * 文本模型调用策略接口。
 * 不同供应商或兼容层可以选择不同协议，但对上层暴露统一入口。
 */
public interface TextModelInvocationStrategy {

    /**
     * 检查是否supports。
     * @param profile profile值
     * @param invocation 调用值
     * @return 是否满足条件
     */
    boolean supports(ModelRuntimeProfile profile, TextModelInvocation invocation);

    /**
     * 处理prepare。
     * @param profile profile值
     * @param invocation 调用值
     * @return 处理结果
     */
    PreparedTextModelRequest prepare(ModelRuntimeProfile profile, TextModelInvocation invocation);
}
