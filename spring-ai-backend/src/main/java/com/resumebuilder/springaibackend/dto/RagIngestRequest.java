// author: jf
package com.resumebuilder.springaibackend.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import java.util.List;

public record RagIngestRequest(
        @NotEmpty(message = "documents 不能为空") List<@Valid RagDocumentInput> documents
) {
}
