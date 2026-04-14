package com.jiandou.api.upload;

import com.jiandou.api.common.exception.ApiException;
import org.springframework.http.HttpStatus;

public final class EmptyUploadFileException extends ApiException {

    public EmptyUploadFileException() {
        super(HttpStatus.BAD_REQUEST, "UPLOAD_FILE_EMPTY", "上传文件不能为空");
    }
}
