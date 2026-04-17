package com.jiandou.api.auth.application;

import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import com.jiandou.api.config.JiandouAuthProperties;
import java.security.SecureRandom;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

/**
 * 首个管理员引导服务。
 */
@Component
public class AuthBootstrapService implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AuthBootstrapService.class);
    private static final String PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";

    private final MybatisAuthRepository authRepository;
    private final JiandouAuthProperties authProperties;
    private final PasswordEncoder passwordEncoder;
    private final SecureRandom secureRandom = new SecureRandom();

    public AuthBootstrapService(
        MybatisAuthRepository authRepository,
        JiandouAuthProperties authProperties,
        PasswordEncoder passwordEncoder
    ) {
        this.authRepository = authRepository;
        this.authProperties = authProperties;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (authRepository.countAdmins() > 0) {
            return;
        }
        JiandouAuthProperties.InitialAdmin initialAdmin = authProperties.getBootstrap().getInitialAdmin();
        String username = AuthApplicationService.validateUsername(initialAdmin.getUsername());
        String displayName = AuthApplicationService.validateDisplayName(initialAdmin.getDisplayName());
        String rawPassword = initialAdmin.getPassword();
        boolean generatedPassword = rawPassword == null || rawPassword.isBlank();
        if (generatedPassword) {
            rawPassword = generatePassword();
        } else {
            rawPassword = AuthApplicationService.validatePassword(rawPassword);
        }
        SysUserEntity createdUser = authRepository.bootstrapInitialAdmin(
            username,
            displayName,
            passwordEncoder.encode(rawPassword)
        );
        if (createdUser == null) {
            return;
        }
        if (generatedPassword) {
            log.warn("初始化首个管理员成功。username={} password={}", createdUser.getUsername(), rawPassword);
        } else {
            log.info("初始化首个管理员成功。username={}", createdUser.getUsername());
        }
    }

    private String generatePassword() {
        StringBuilder builder = new StringBuilder(16);
        for (int index = 0; index < 16; index++) {
            builder.append(PASSWORD_ALPHABET.charAt(secureRandom.nextInt(PASSWORD_ALPHABET.length())));
        }
        return builder.toString();
    }
}
