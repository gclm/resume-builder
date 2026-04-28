// author: jf
package com.resumebuilder.springaibackend.chunking;

import com.resumebuilder.springaibackend.parser.RagDocumentParserService;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class RagChunkingService {

    public List<RagChunk> chunk(RagDocumentParserService.ParsedRagDocument document, int chunkSize, int chunkOverlap) {
        int safeChunkSize = Math.max(200, chunkSize);
        int safeOverlap = Math.max(0, Math.min(chunkOverlap, safeChunkSize / 2));
        List<String> logicalParts = splitLogicalParts(document.content());
        List<RagChunk> chunks = new ArrayList<>();

        for (String logicalPart : logicalParts) {
            for (String content : chunkText(logicalPart, safeChunkSize, safeOverlap)) {
                if (StringUtils.hasText(content)) {
                    chunks.add(new RagChunk(document.sourceId(), chunks.size(), content));
                }
            }
        }
        return chunks;
    }

    private static List<String> splitLogicalParts(String content) {
        String safeContent = safeText(content);
        if (safeContent.isBlank()) {
            return List.of();
        }

        List<String> parts = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        for (String block : safeContent.split("\\n\\s*\\n")) {
            String normalizedBlock = block.trim();
            if (!StringUtils.hasText(normalizedBlock)) {
                continue;
            }
            boolean heading = isHeading(normalizedBlock);
            if (heading && !current.isEmpty()) {
                parts.add(current.toString().trim());
                current.setLength(0);
            }
            if (!current.isEmpty()) {
                current.append("\n\n");
            }
            current.append(normalizedBlock);
        }
        if (!current.isEmpty()) {
            parts.add(current.toString().trim());
        }
        return parts.isEmpty() ? List.of(safeContent) : parts;
    }

    private static List<String> chunkText(String content, int chunkSize, int chunkOverlap) {
        String safeContent = safeText(content);
        if (safeContent.length() <= chunkSize) {
            return List.of(safeContent);
        }

        List<String> chunks = new ArrayList<>();
        int start = 0;
        while (start < safeContent.length()) {
            int targetEnd = Math.min(start + chunkSize, safeContent.length());
            int end = resolveChunkEnd(safeContent, start, targetEnd);
            String chunk = safeContent.substring(start, end).trim();
            if (StringUtils.hasText(chunk)) {
                chunks.add(chunk);
            }
            if (end >= safeContent.length()) {
                break;
            }
            start = Math.max(end - chunkOverlap, start + 1);
        }
        return chunks;
    }

    private static int resolveChunkEnd(String content, int start, int targetEnd) {
        if (targetEnd >= content.length()) {
            return content.length();
        }
        int paragraphBreak = content.lastIndexOf("\n\n", targetEnd);
        if (paragraphBreak > start + 120) {
            return paragraphBreak;
        }
        int lineBreak = content.lastIndexOf('\n', targetEnd);
        if (lineBreak > start + 120) {
            return lineBreak;
        }
        int sentenceBreak = Math.max(content.lastIndexOf('。', targetEnd), content.lastIndexOf('；', targetEnd));
        if (sentenceBreak > start + 120) {
            return sentenceBreak + 1;
        }
        return targetEnd;
    }

    private static boolean isHeading(String block) {
        String compact = safeText(block);
        if (compact.length() > 80 || compact.contains("\n")) {
            return false;
        }
        return compact.startsWith("#")
                || compact.matches("^\\d+[.)、].+")
                || compact.matches("^[Qq]\\d*[:：].+")
                || compact.endsWith("?");
    }

    private static String safeText(String value) {
        return value == null ? "" : value.trim();
    }

    public record RagChunk(String sourceId, int chunkIndex, String content) {
    }
}
