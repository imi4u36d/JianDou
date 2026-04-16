package com.jiandou.api.config;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.InitializingBean;

class DatabaseSchemaInitializerTest {

    @Test
    void databaseSchemaRunnerIgnoresKnownSchemaErrors() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection connection = mock(Connection.class);
        Statement statement = mock(Statement.class);
        DatabaseMetaData metadata = mock(DatabaseMetaData.class);
        when(dataSource.getConnection()).thenReturn(connection);
        when(connection.createStatement()).thenReturn(statement);
        when(connection.getMetaData()).thenReturn(metadata);
        when(metadata.getColumns(eq(null), eq(null), anyString(), anyString())).thenAnswer(invocation -> emptyColumns());
        when(statement.execute(anyString())).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0, String.class);
            if (sql.startsWith("CREATE INDEX `idx_task_attempts_status_queue_entered_at`")) {
                throw new SQLException("duplicate index", "42000", 1061);
            }
            return true;
        });

        InitializingBean runner = new DatabaseSchemaInitializer().databaseSchemaRunner(dataSource);

        assertDoesNotThrow(runner::afterPropertiesSet);
        verify(statement, atLeastOnce()).execute(anyString());
    }

    @Test
    void databaseSchemaRunnerWidensNarrowUrlColumns() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection connection = mock(Connection.class);
        Statement statement = mock(Statement.class);
        DatabaseMetaData metadata = mock(DatabaseMetaData.class);
        when(dataSource.getConnection()).thenReturn(connection);
        when(connection.createStatement()).thenReturn(statement);
        when(connection.getMetaData()).thenReturn(metadata);
        when(metadata.getColumns(eq(null), eq(null), anyString(), anyString())).thenAnswer(invocation -> {
            String table = invocation.getArgument(2, String.class);
            String column = invocation.getArgument(3, String.class);
            if ("biz_task_results".equals(table) && "preview_path".equals(column)) {
                return narrowVarcharColumn();
            }
            return emptyColumns();
        });
        when(statement.execute(anyString())).thenReturn(true);

        InitializingBean runner = new DatabaseSchemaInitializer().databaseSchemaRunner(dataSource);

        runner.afterPropertiesSet();

        verify(statement).execute("ALTER TABLE `biz_task_results` MODIFY COLUMN `preview_path` TEXT NOT NULL");
        verify(statement, never()).execute("ALTER TABLE `biz_task_results` MODIFY COLUMN `download_path` TEXT NOT NULL");
    }

    private ResultSet emptyColumns() throws SQLException {
        ResultSet resultSet = mock(ResultSet.class);
        when(resultSet.next()).thenReturn(false);
        return resultSet;
    }

    private ResultSet narrowVarcharColumn() throws SQLException {
        ResultSet resultSet = mock(ResultSet.class);
        when(resultSet.next()).thenReturn(true, false);
        when(resultSet.getString("TYPE_NAME")).thenReturn("VARCHAR");
        when(resultSet.getInt("COLUMN_SIZE")).thenReturn(255);
        return resultSet;
    }
}
