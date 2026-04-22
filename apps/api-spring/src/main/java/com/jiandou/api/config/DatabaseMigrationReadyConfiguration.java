package com.jiandou.api.config;

import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationVersion;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 数据库迁移完成标记配置。
 */
@Configuration
public class DatabaseMigrationReadyConfiguration {

    @Bean
    public Flyway flyway(DataSource dataSource) {
        return Flyway.configure()
            .dataSource(dataSource)
            .locations("classpath:db/migration")
            .baselineOnMigrate(true)
            .baselineVersion(MigrationVersion.fromVersion("1"))
            .validateOnMigrate(true)
            .load();
    }

    /**
     * 暴露数据库可用标记，兼容依赖旧 bean 名称的组件。
     * @param flyway Flyway 对象
     * @return 标记对象
     */
    @Bean("databaseSchemaReady")
    public InitializingBean databaseSchemaReady(Flyway flyway) {
        return flyway::migrate;
    }
}
