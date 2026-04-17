package com.jiandou.api.config;

/**
 * 统一管理后端公开路径常量，避免多个控制器和 Web 配置重复硬编码。
 */
public final class ApiPathConstants {

    public static final String API_V2 = "/api/v2";
    public static final String API_V2_PATTERN = API_V2 + "/**";
    public static final String HEALTH = API_V2 + "/health";
    public static final String STORAGE = "/storage";
    public static final String STORAGE_PATTERN = STORAGE + "/**";
    public static final String AUTH = API_V2 + "/auth";
    public static final String AUTH_PATTERN = AUTH + "/**";
    public static final String AUTH_SESSION = AUTH + "/session";
    public static final String AUTH_LOGIN = AUTH + "/login";
    public static final String AUTH_LOGOUT = AUTH + "/logout";
    public static final String AUTH_ACTIVATE_INVITE = AUTH + "/activate-invite";
    public static final String TASKS = API_V2 + "/tasks";
    public static final String UPLOADS = API_V2 + "/uploads";
    public static final String ADMIN = API_V2 + "/admin";
    public static final String ADMIN_PATTERN = ADMIN + "/**";
    public static final String GENERATION = API_V2 + "/generation";

    private ApiPathConstants() {
    }
}
