package com.jiandou.api.generation.text;

import com.jiandou.api.generation.ModelRuntimeProfile;

/**
 * 文本模型调用策略接口。
 * 不同供应商或兼容层可以选择不同协议，但对上层暴露统一入口。
 */
public interface TextModelInvocationStrategy {

    boolean supports(ModelRuntimeProfile profile, TextModelInvocation invocation);

    PreparedTextModelRequest prepare(ModelRuntimeProfile profile, TextModelInvocation invocation);
}
