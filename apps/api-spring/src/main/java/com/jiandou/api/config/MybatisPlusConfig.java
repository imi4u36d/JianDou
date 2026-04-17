package com.jiandou.api.config;

import com.baomidou.mybatisplus.core.config.GlobalConfig;
import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.MybatisSqlSessionFactoryBuilder;
import com.jiandou.api.auth.infrastructure.mybatis.SysInviteCodeMapper;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserMapper;
import com.jiandou.api.task.infrastructure.mybatis.TaskAttemptMapper;
import com.jiandou.api.task.infrastructure.mybatis.TaskModelCallMapper;
import com.jiandou.api.task.infrastructure.mybatis.MaterialAssetMapper;
import com.jiandou.api.task.infrastructure.mybatis.SystemLogMapper;
import com.jiandou.api.task.infrastructure.mybatis.TaskMapper;
import com.jiandou.api.task.infrastructure.mybatis.TaskQueueEventMapper;
import com.jiandou.api.task.infrastructure.mybatis.TaskResultMapper;
import com.jiandou.api.task.infrastructure.mybatis.TaskStageRunMapper;
import com.jiandou.api.task.infrastructure.mybatis.TaskStatusHistoryMapper;
import com.jiandou.api.task.infrastructure.mybatis.WorkerInstanceMapper;
import com.zaxxer.hikari.HikariDataSource;
import javax.sql.DataSource;
import org.apache.ibatis.mapping.Environment;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * MyBatisPlus配置。
 */
@Configuration
public class MybatisPlusConfig {

    /**
     * 处理data来源。
     * @return 处理结果
     */
    @Bean
    public DataSource dataSource(
        @Value("${spring.datasource.url}") String url,
        @Value("${spring.datasource.username}") String username,
        @Value("${spring.datasource.password}") String password,
        @Value("${spring.datasource.driver-class-name}") String driverClassName
    ) {
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setJdbcUrl(url);
        dataSource.setUsername(username);
        dataSource.setPassword(password);
        dataSource.setDriverClassName(driverClassName);
        dataSource.setMaximumPoolSize(6);
        dataSource.setMinimumIdle(1);
        dataSource.setConnectionTimeout(30_000);
        return dataSource;
    }

    /**
     * 处理sqlSession工厂。
     * @param dataSource data来源值
     * @return 处理结果
     */
    @Bean
    public SqlSessionFactory sqlSessionFactory(DataSource dataSource) {
        MybatisConfiguration configuration = new MybatisConfiguration();
        configuration.setMapUnderscoreToCamelCase(true);
        configuration.setEnvironment(new Environment("jiandou", new JdbcTransactionFactory(), dataSource));
        configuration.addMapper(TaskMapper.class);
        configuration.addMapper(TaskAttemptMapper.class);
        configuration.addMapper(TaskStageRunMapper.class);
        configuration.addMapper(TaskStatusHistoryMapper.class);
        configuration.addMapper(TaskModelCallMapper.class);
        configuration.addMapper(TaskResultMapper.class);
        configuration.addMapper(MaterialAssetMapper.class);
        configuration.addMapper(SystemLogMapper.class);
        configuration.addMapper(TaskQueueEventMapper.class);
        configuration.addMapper(WorkerInstanceMapper.class);
        configuration.addMapper(SysUserMapper.class);
        configuration.addMapper(SysInviteCodeMapper.class);

        GlobalConfig config = new GlobalConfig();
        config.setBanner(false);
        return new MybatisSqlSessionFactoryBuilder().build(configuration);
    }

    /**
     * 处理全局配置。
     * @return 处理结果
     */
    @Bean
    public GlobalConfig globalConfig() {
        GlobalConfig config = new GlobalConfig();
        config.setBanner(false);
        return config;
    }
}
