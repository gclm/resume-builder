// author: jf
package com.resumebuilder.springaibackend.parser;

import com.resumebuilder.springaibackend.ocr.OpenAiVisionOcrService;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Set;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

@Component
public class RagDocumentParserService {

    private static final Set<String> TEXT_EXTENSIONS = Set.of(".txt", ".md");
    private static final Set<String> DOCUMENT_EXTENSIONS = Set.of(".pdf", ".txt", ".md", ".docx");
    private static final Set<String> IMAGE_EXTENSIONS = Set.of(".png", ".jpg", ".jpeg", ".webp");

    private final OpenAiVisionOcrService openAiVisionOcrService;

    public RagDocumentParserService(OpenAiVisionOcrService openAiVisionOcrService) {
        this.openAiVisionOcrService = openAiVisionOcrService;
    }

    public ParsedRagDocument parse(MultipartFile file, int maxFileSizeMb) {
        String fileName = safeFileName(file);
        String extension = extensionOf(fileName);
        String contentType = StringUtils.hasText(file.getContentType())
                ? file.getContentType().trim()
                : "application/octet-stream";
        byte[] fileBytes = readBytes(file, maxFileSizeMb);

        if (IMAGE_EXTENSIONS.contains(extension)) {
            String content = openAiVisionOcrService.extractMarkdown(fileBytes, fileName, contentType);
            return new ParsedRagDocument(sourceId(fileName), fileName, contentType, "image", "image_ocr_text", normalizeContent(content));
        }
        if (!DOCUMENT_EXTENSIONS.contains(extension)) {
            throw new IllegalArgumentException("暂不支持的文件类型: " + (extension.isBlank() ? contentType : extension));
        }

        String content;
        if (TEXT_EXTENSIONS.contains(extension)) {
            content = decodeText(fileBytes);
        } else if (".pdf".equals(extension)) {
            content = parsePdf(fileBytes);
        } else if (".docx".equals(extension)) {
            content = parseDocx(fileBytes);
        } else {
            throw new IllegalArgumentException("暂不支持的文件类型: " + extension);
        }
        return new ParsedRagDocument(sourceId(fileName), fileName, contentType, "document", "text_document", normalizeContent(content));
    }

    private static byte[] readBytes(MultipartFile file, int maxFileSizeMb) {
        int safeMaxFileSizeMb = Math.max(1, maxFileSizeMb);
        long byteLimit = safeMaxFileSizeMb * 1024L * 1024L;
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("上传文件不能为空");
        }
        if (file.getSize() > byteLimit) {
            throw new IllegalArgumentException("文件 " + safeFileName(file) + " 超过大小限制 " + safeMaxFileSizeMb + "MB");
        }
        try {
            byte[] fileBytes = file.getBytes();
            if (fileBytes.length == 0) {
                throw new IllegalArgumentException("上传文件不能为空");
            }
            if (fileBytes.length > byteLimit) {
                throw new IllegalArgumentException("文件 " + safeFileName(file) + " 超过大小限制 " + safeMaxFileSizeMb + "MB");
            }
            return fileBytes;
        } catch (IOException ex) {
            throw new IllegalArgumentException("读取上传文件失败: " + ex.getMessage(), ex);
        }
    }

    private static String decodeText(byte[] fileBytes) {
        for (Charset charset : new Charset[]{StandardCharsets.UTF_8, Charset.forName("GBK")}) {
            try {
                return charset.newDecoder()
                        .onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT)
                        .decode(ByteBuffer.wrap(fileBytes))
                        .toString();
            } catch (CharacterCodingException ignored) {
                // 继续尝试下一个编码，最后用 UTF-8 replace 兜底。
            }
        }
        return StandardCharsets.UTF_8.decode(ByteBuffer.wrap(fileBytes)).toString();
    }

    private static String parsePdf(byte[] fileBytes) {
        try (PDDocument document = PDDocument.load(new ByteArrayInputStream(fileBytes))) {
            PDFTextStripper stripper = new PDFTextStripper();
            return stripper.getText(document);
        } catch (IOException ex) {
            throw new IllegalArgumentException("PDF 解析失败: " + ex.getMessage(), ex);
        }
    }

    private static String parseDocx(byte[] fileBytes) {
        try (XWPFDocument document = new XWPFDocument(new ByteArrayInputStream(fileBytes))) {
            return document.getParagraphs().stream()
                    .map(XWPFParagraph::getText)
                    .map(RagDocumentParserService::safeText)
                    .filter(StringUtils::hasText)
                    .reduce((left, right) -> left + "\n\n" + right)
                    .orElse("");
        } catch (IOException ex) {
            throw new IllegalArgumentException("DOCX 解析失败: " + ex.getMessage(), ex);
        }
    }

    private static String normalizeContent(String content) {
        String normalized = safeText(content)
                .replace("\uFEFF", "")
                .replace("\r\n", "\n")
                .replace('\r', '\n')
                .replaceAll("[ \\t]+\\n", "\n")
                .replaceAll("\\n{3,}", "\n\n")
                .trim();
        if (!StringUtils.hasText(normalized)) {
            throw new IllegalArgumentException("文件未解析到可入库内容");
        }
        return normalized;
    }

    private static String safeFileName(MultipartFile file) {
        String original = file == null ? "" : safeText(file.getOriginalFilename());
        return original.isBlank() ? "upload.bin" : original;
    }

    private static String sourceId(String fileName) {
        String safeName = safeText(fileName);
        int dotIndex = safeName.lastIndexOf('.');
        String stem = dotIndex > 0 ? safeName.substring(0, dotIndex) : safeName;
        return stem.isBlank() ? safeName : stem;
    }

    private static String extensionOf(String fileName) {
        String safeName = safeText(fileName).toLowerCase(Locale.ROOT);
        int dotIndex = safeName.lastIndexOf('.');
        return dotIndex < 0 ? "" : safeName.substring(dotIndex);
    }

    private static String safeText(String value) {
        return value == null ? "" : value.trim();
    }

    public record ParsedRagDocument(
            String sourceId,
            String originalFilename,
            String originalContentType,
            String sourceType,
            String ingestSource,
            String content
    ) {
    }
}
