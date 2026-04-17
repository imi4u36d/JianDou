package com.jiandou.api.auth.domain;

/**
 * 邀请码状态。
 */
public enum InviteStatus {
    UNUSED,
    USED,
    REVOKED,
    EXPIRED;

    /**
     * 返回状态值。
     * @return 处理结果
     */
    public String value() {
        return name();
    }
}
