package com.jiandou.api.upload.exception;

import com.jiandou.api.common.exception.ApiException;
import org.springframework.http.HttpStatus;

/**
 * 上传Failed异常。
 */
public final class UploadFailedException extends ApiException {

    /**
     * 创建新的上传Failed异常。
     * @param message 消息文本
     * @param cause cause值
     */
    public UploadFailedException(String message, Throwable cause) {
        super(HttpStatus.INTERNAL_SERVER_ERROR, "UPLOAD_SAVE_FAILED", message, cause);
    }
}
