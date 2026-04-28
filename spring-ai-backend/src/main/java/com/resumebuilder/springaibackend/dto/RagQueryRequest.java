// author: jf
package com.resumebuilder.springaibackend.dto;

import jakarta.validation.constraints.NotBlank;

public record RagQueryRequest(
        @NotBlank(message = "query 不能为空") String query,
        Integer topK
) {
}
