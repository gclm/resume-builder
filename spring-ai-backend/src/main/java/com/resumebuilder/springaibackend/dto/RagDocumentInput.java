// author: jf
package com.resumebuilder.springaibackend.dto;

import jakarta.validation.constraints.NotBlank;
import java.util.Map;

public record RagDocumentInput(
        String sourceId,
        @NotBlank(message = "文档内容不能为空") String content,
        Map<String, Object> metadata
) {
}
