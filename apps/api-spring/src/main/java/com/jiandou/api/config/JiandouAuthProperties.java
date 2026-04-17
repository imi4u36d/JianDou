package com.jiandou.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 鉴权相关配置。
 */
@ConfigurationProperties(prefix = "jiandou.auth")
public class JiandouAuthProperties {

    private int inviteDefaultExpiryDays = 7;
    private final Bootstrap bootstrap = new Bootstrap();

    public int getInviteDefaultExpiryDays() {
        return inviteDefaultExpiryDays;
    }

    public void setInviteDefaultExpiryDays(int inviteDefaultExpiryDays) {
        this.inviteDefaultExpiryDays = inviteDefaultExpiryDays <= 0 ? 7 : inviteDefaultExpiryDays;
    }

    public Bootstrap getBootstrap() {
        return bootstrap;
    }

    /**
     * 首个管理员引导配置。
     */
    public static class Bootstrap {

        private final InitialAdmin initialAdmin = new InitialAdmin();

        public InitialAdmin getInitialAdmin() {
            return initialAdmin;
        }
    }

    /**
     * 首个管理员配置。
     */
    public static class InitialAdmin {

        private String username = "admin";
        private String displayName = "系统管理员";
        private String password = "";

        public String getUsername() {
            return username;
        }

        public void setUsername(String username) {
            this.username = username == null ? "admin" : username.trim();
        }

        public String getDisplayName() {
            return displayName;
        }

        public void setDisplayName(String displayName) {
            this.displayName = displayName == null ? "系统管理员" : displayName.trim();
        }

        public String getPassword() {
            return password;
        }

        public void setPassword(String password) {
            this.password = password == null ? "" : password.trim();
        }
    }
}
