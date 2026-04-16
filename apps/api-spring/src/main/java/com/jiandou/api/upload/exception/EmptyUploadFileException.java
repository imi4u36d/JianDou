package com.jiandou.api.upload.exception;

import com.jiandou.api.common.exception.ApiException;
import org.springframework.http.HttpStatus;

/**
 * Empty上传文件异常。
 */
public final class EmptyUploadFileException extends ApiException {

    /**
     * 创建新的Empty上传文件异常。
     */
    public EmptyUploadFileException() {
        super(HttpStatus.BAD_REQUEST, "UPLOAD_FILE_EMPTY", "上传文件不能为空");
    }
}
