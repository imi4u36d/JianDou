package com.jiandou.api.upload;

public final class UploadFailedException extends RuntimeException {

    public UploadFailedException(String message, Throwable cause) {
        super(message, cause);
    }
}
