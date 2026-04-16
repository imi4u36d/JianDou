package com.jiandou.api.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;

import com.baomidou.mybatisplus.core.config.GlobalConfig;
import com.jiandou.api.task.infrastructure.mybatis.TaskMapper;
import com.jiandou.api.task.infrastructure.mybatis.WorkerInstanceMapper;
import com.zaxxer.hikari.HikariDataSource;
import javax.sql.DataSource;
import org.apache.ibatis.session.SqlSessionFactory;
import org.junit.jupiter.api.Test;

class MybatisPlusConfigTest {

    private final MybatisPlusConfig config = new MybatisPlusConfig();

    @Test
    void dataSourceBuildsExpectedHikariConfiguration() {
        DataSource dataSource = config.dataSource("jdbc:mysql://127.0.0.1:3306/jiandou", "user", "pass", "com.mysql.cj.jdbc.Driver");

        HikariDataSource hikari = (HikariDataSource) dataSource;
        assertEquals("jdbc:mysql://127.0.0.1:3306/jiandou", hikari.getJdbcUrl());
        assertEquals("user", hikari.getUsername());
        assertEquals("pass", hikari.getPassword());
        assertEquals("com.mysql.cj.jdbc.Driver", hikari.getDriverClassName());
        assertEquals(6, hikari.getMaximumPoolSize());
        assertEquals(1, hikari.getMinimumIdle());
        assertEquals(30_000L, hikari.getConnectionTimeout());
        hikari.close();
    }

    @Test
    void sqlSessionFactoryRegistersEnvironmentAndMappers() throws Exception {
        DataSource dataSource = mock(DataSource.class);

        SqlSessionFactory sqlSessionFactory = config.sqlSessionFactory(dataSource);

        assertTrue(sqlSessionFactory.getConfiguration().isMapUnderscoreToCamelCase());
        assertEquals("jiandou", sqlSessionFactory.getConfiguration().getEnvironment().getId());
        assertTrue(sqlSessionFactory.getConfiguration().getMapperRegistry().hasMapper(TaskMapper.class));
        assertTrue(sqlSessionFactory.getConfiguration().getMapperRegistry().hasMapper(WorkerInstanceMapper.class));
    }

    @Test
    void globalConfigDisablesBanner() {
        GlobalConfig globalConfig = config.globalConfig();

        assertFalse(globalConfig.isBanner());
    }
}
