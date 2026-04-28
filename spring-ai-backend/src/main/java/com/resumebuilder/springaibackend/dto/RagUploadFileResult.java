// author: jf
package com.resumebuilder.springaibackend.dto;

public record RagUploadFileResult(
        String fileName,
        String contentType,
        String sourceType,
        String ingestSource,
        int chunkCount,
        int insertedCount,
        String status,
        String errorMessage
) {
}
