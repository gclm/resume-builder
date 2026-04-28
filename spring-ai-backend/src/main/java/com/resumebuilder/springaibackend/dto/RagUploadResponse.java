// author: jf
package com.resumebuilder.springaibackend.dto;

import java.util.List;

public record RagUploadResponse(
        int totalFiles,
        int succeededFiles,
        int failedFiles,
        int inserted,
        List<RagUploadFileResult> files
) {
}
