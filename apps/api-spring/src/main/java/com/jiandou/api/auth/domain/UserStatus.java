package com.jiandou.api.auth.domain;

/**
 * 用户状态。
 */
public enum UserStatus {
    ACTIVE,
    DISABLED;

    /**
     * 返回状态值。
     * @return 处理结果
     */
    public String value() {
        return name();
    }
}
