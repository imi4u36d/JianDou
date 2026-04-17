package com.jiandou.api.auth.domain;

/**
 * 用户角色。
 */
public enum UserRole {
    ADMIN,
    USER;

    /**
     * 返回角色值。
     * @return 处理结果
     */
    public String value() {
        return name();
    }

    /**
     * 解析角色。
     * @param raw 原始值
     * @return 处理结果
     */
    public static UserRole from(String raw) {
        if (raw == null || raw.isBlank()) {
            throw new IllegalArgumentException("角色不能为空");
        }
        return UserRole.valueOf(raw.trim().toUpperCase());
    }
}
