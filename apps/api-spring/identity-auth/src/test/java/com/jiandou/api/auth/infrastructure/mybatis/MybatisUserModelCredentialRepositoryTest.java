package com.jiandou.api.auth.infrastructure.mybatis;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.junit.jupiter.api.Test;

class MybatisUserModelCredentialRepositoryTest {

    @Test
    void runtimeApiKeyForNonAdminUsesAdminCredentialUser() {
        SqlSessionFactory sqlSessionFactory = mock(SqlSessionFactory.class);
        SqlSession session = mock(SqlSession.class);
        SysUserMapper userMapper = mock(SysUserMapper.class);
        SysUserModelCredentialMapper credentialMapper = mock(SysUserModelCredentialMapper.class);
        UserModelCredentialCipher cipher = mock(UserModelCredentialCipher.class);
        MybatisUserModelCredentialRepository repository = new MybatisUserModelCredentialRepository(sqlSessionFactory, cipher);
        SysUserEntity normalUser = user(7L, "tester");
        SysUserEntity adminUser = user(1L, "admin");
        SysUserModelCredentialEntity adminCredential = credential(1L, "deepseek", "encrypted-admin-key");

        when(sqlSessionFactory.openSession()).thenReturn(session);
        when(session.getMapper(SysUserMapper.class)).thenReturn(userMapper);
        when(session.getMapper(SysUserModelCredentialMapper.class)).thenReturn(credentialMapper);
        when(userMapper.selectById(7L)).thenReturn(normalUser);
        when(userMapper.selectOne(any())).thenReturn(adminUser);
        when(credentialMapper.selectList(any())).thenReturn(List.of(adminCredential));
        when(cipher.decrypt("encrypted-admin-key")).thenReturn("admin-key");

        String apiKey = repository.findRuntimeApiKey(7L, List.of("deepseek"));

        assertEquals("admin-key", apiKey);
    }

    @Test
    void runtimeApiKeyForAdminUsesOwnCredentials() {
        SqlSessionFactory sqlSessionFactory = mock(SqlSessionFactory.class);
        SqlSession session = mock(SqlSession.class);
        SysUserMapper userMapper = mock(SysUserMapper.class);
        SysUserModelCredentialMapper credentialMapper = mock(SysUserModelCredentialMapper.class);
        UserModelCredentialCipher cipher = mock(UserModelCredentialCipher.class);
        MybatisUserModelCredentialRepository repository = new MybatisUserModelCredentialRepository(sqlSessionFactory, cipher);
        SysUserEntity adminUser = user(1L, "admin");
        SysUserModelCredentialEntity adminCredential = credential(1L, "deepseek", "encrypted-admin-key");

        when(sqlSessionFactory.openSession()).thenReturn(session);
        when(session.getMapper(SysUserMapper.class)).thenReturn(userMapper);
        when(session.getMapper(SysUserModelCredentialMapper.class)).thenReturn(credentialMapper);
        when(userMapper.selectById(1L)).thenReturn(adminUser);
        when(credentialMapper.selectList(any())).thenReturn(List.of(adminCredential));
        when(cipher.decrypt("encrypted-admin-key")).thenReturn("admin-key");

        String apiKey = repository.findRuntimeApiKey(1L, List.of("deepseek"));

        assertEquals("admin-key", apiKey);
        verify(userMapper, never()).selectOne(any());
    }

    @Test
    void runtimeApiKeyDoesNotFallbackToNormalUserWhenAdminKeyMissing() {
        SqlSessionFactory sqlSessionFactory = mock(SqlSessionFactory.class);
        SqlSession session = mock(SqlSession.class);
        SysUserMapper userMapper = mock(SysUserMapper.class);
        SysUserModelCredentialMapper credentialMapper = mock(SysUserModelCredentialMapper.class);
        UserModelCredentialCipher cipher = mock(UserModelCredentialCipher.class);
        MybatisUserModelCredentialRepository repository = new MybatisUserModelCredentialRepository(sqlSessionFactory, cipher);
        SysUserEntity normalUser = user(7L, "tester");
        SysUserEntity adminUser = user(1L, "admin");

        when(sqlSessionFactory.openSession()).thenReturn(session);
        when(session.getMapper(SysUserMapper.class)).thenReturn(userMapper);
        when(session.getMapper(SysUserModelCredentialMapper.class)).thenReturn(credentialMapper);
        when(userMapper.selectById(7L)).thenReturn(normalUser);
        when(userMapper.selectOne(any())).thenReturn(adminUser);
        when(credentialMapper.selectList(any())).thenReturn(List.of());

        String apiKey = repository.findRuntimeApiKey(7L, List.of("deepseek"));

        assertEquals("", apiKey);
    }

    @Test
    void runtimeCredentialUserIdForNonAdminIsAdminUserId() {
        MybatisUserModelCredentialRepository repository = new MybatisUserModelCredentialRepository(
            mock(SqlSessionFactory.class),
            mock(UserModelCredentialCipher.class)
        );

        assertEquals(1L, repository.resolveRuntimeCredentialUserId(7L, "tester", 1L));
    }

    @Test
    void runtimeCredentialUserIdForAdminIsOwnUserId() {
        MybatisUserModelCredentialRepository repository = new MybatisUserModelCredentialRepository(
            mock(SqlSessionFactory.class),
            mock(UserModelCredentialCipher.class)
        );

        assertEquals(1L, repository.resolveRuntimeCredentialUserId(1L, "admin", 9L));
    }

    private SysUserEntity user(Long id, String username) {
        SysUserEntity user = new SysUserEntity();
        user.setId(id);
        user.setUsername(username);
        return user;
    }

    private SysUserModelCredentialEntity credential(Long userId, String providerKey, String encryptedApiKey) {
        SysUserModelCredentialEntity entity = new SysUserModelCredentialEntity();
        entity.setUserId(userId);
        entity.setProviderKey(providerKey);
        entity.setEncryptedApiKey(encryptedApiKey);
        return entity;
    }
}
