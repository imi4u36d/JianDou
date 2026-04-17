package com.jiandou.api.config;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class JiandouAppPropertiesTest {

    @Test
    void settersTrimValuesAndApplyDefaults() {
        JiandouAppProperties properties = new JiandouAppProperties();
        properties.setEnv(" prod ");
        properties.setExecutionMode(" Worker ");
        properties.setWebOrigin(" https://example.com ");

        assertEquals("prod", properties.getEnv());
        assertEquals("worker", properties.getExecutionMode());
        assertEquals("https://example.com", properties.getWebOrigin());

        properties.setEnv(null);
        properties.setExecutionMode(null);
        properties.setWebOrigin(null);

        assertEquals("dev", properties.getEnv());
        assertEquals("queue", properties.getExecutionMode());
        assertEquals("", properties.getWebOrigin());
    }

    @Test
    void unknownExecutionModeStillFallsBackToNormalizedString() {
        JiandouAppProperties properties = new JiandouAppProperties();

        properties.setExecutionMode(" sync ");

        assertEquals("sync", properties.getExecutionMode());
    }

    @Test
    void resolveCookieSameSiteUsesSecureAwareDefaults() {
        JiandouAppProperties properties = new JiandouAppProperties();

        assertEquals("Lax", properties.resolveCookieSameSite());

        properties.setCookieSecure(true);

        assertEquals("None", properties.resolveCookieSameSite());
    }
}
