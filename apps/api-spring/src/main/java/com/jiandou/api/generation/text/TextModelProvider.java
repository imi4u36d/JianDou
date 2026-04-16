package com.jiandou.api.generation.text;

import com.jiandou.api.generation.runtime.ModelRuntimeProfile;
import com.jiandou.api.generation.TextModelResponse;

/**
 * 文本模型 provider SPI。
 */
public interface TextModelProvider {

    /**
     * 检查是否支持当前 profile。
     * @param profile 运行时配置值
     * @return 是否满足条件
     */
    boolean supports(ModelRuntimeProfile profile);

    /**
     * 执行文本生成。
     * @param profile 运行时配置值
     * @param invocation 调用值
     * @return 处理结果
     */
    TextModelResponse generate(ModelRuntimeProfile profile, TextModelInvocation invocation);
}
