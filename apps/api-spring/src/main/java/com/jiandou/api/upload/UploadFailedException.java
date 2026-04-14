package com.jiandou.api.upload;

import com.jiandou.api.common.exception.ApiException;
import org.springframework.http.HttpStatus;

public final class UploadFailedException extends ApiException {

    public UploadFailedException(String message, Throwable cause) {
        super(HttpStatus.INTERNAL_SERVER_ERROR, "UPLOAD_SAVE_FAILED", message, cause);
    }
}
