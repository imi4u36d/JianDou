package com.jiandou.api.config;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import javax.sql.DataSource;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DatabaseSchemaInitializer {

    @Bean("databaseSchemaReady")
    public InitializingBean databaseSchemaRunner(DataSource dataSource) {
        return () -> initializeSchema(dataSource);
    }

    private void initializeSchema(DataSource dataSource) throws SQLException, IOException {
        String script;
        try (InputStream inputStream = Thread.currentThread().getContextClassLoader().getResourceAsStream("schema.sql")) {
            if (inputStream == null) {
                return;
            }
            script = new String(inputStream.readAllBytes(), StandardCharsets.UTF_8);
        }
        try (Connection connection = dataSource.getConnection(); Statement statement = connection.createStatement()) {
            for (String rawSql : script.split(";")) {
                String sql = rawSql.trim();
                if (!sql.isEmpty()) {
                    try {
                        statement.execute(sql);
                    } catch (SQLException ex) {
                        if (!isIgnorableSchemaError(ex)) {
                            throw ex;
                        }
                    }
                }
            }
        }
    }

    private boolean isIgnorableSchemaError(SQLException ex) {
        return ex.getErrorCode() == 1061 || ex.getErrorCode() == 1060;
    }
}
