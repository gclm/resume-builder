// author: jf
package com.resumebuilder.springaibackend.controller;

import com.resumebuilder.springaibackend.dto.ChatRequest;
import com.resumebuilder.springaibackend.dto.ChatResponse;
import com.resumebuilder.springaibackend.dto.RagIngestRequest;
import com.resumebuilder.springaibackend.dto.RagIngestResponse;
import com.resumebuilder.springaibackend.dto.RagQueryRequest;
import com.resumebuilder.springaibackend.dto.RagQueryResponse;
import com.resumebuilder.springaibackend.dto.RagUploadResponse;
import com.resumebuilder.springaibackend.dto.RealtimeClientSecretRequest;
import com.resumebuilder.springaibackend.dto.RealtimeClientSecretResponse;
import com.resumebuilder.springaibackend.dto.InterviewSessionDetailResponse;
import com.resumebuilder.springaibackend.dto.InterviewSessionSummaryResponse;
import com.resumebuilder.springaibackend.dto.InterviewStreamEvent;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest;
import com.resumebuilder.springaibackend.service.AiGatewayService;
import com.resumebuilder.springaibackend.service.RagService;
import com.resumebuilder.springaibackend.service.RealtimeSessionService;
import com.resumebuilder.springaibackend.service.InterviewSessionStoreService;
import com.resumebuilder.springaibackend.service.InterviewTurnService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/api/ai")
public class AiController {

    private final AiGatewayService aiGatewayService;
    private final InterviewTurnService interviewTurnService;
    private final RealtimeSessionService realtimeSessionService;
    private final InterviewSessionStoreService interviewSessionStoreService;
    private final RagService ragService;

    public AiController(
            AiGatewayService aiGatewayService,
            InterviewTurnService interviewTurnService,
            RealtimeSessionService realtimeSessionService,
            InterviewSessionStoreService interviewSessionStoreService,
            RagService ragService
    ) {
        this.aiGatewayService = aiGatewayService;
        this.interviewTurnService = interviewTurnService;
        this.realtimeSessionService = realtimeSessionService;
        this.interviewSessionStoreService = interviewSessionStoreService;
        this.ragService = ragService;
    }

    @PostMapping("/chat")
    public ChatResponse chat(@Valid @RequestBody ChatRequest request) {
        boolean sanitize = Boolean.TRUE.equals(request.sanitizeOutput());
        return new ChatResponse(aiGatewayService.chat(request.message(), sanitize));
    }

    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> streamChat(@Valid @RequestBody ChatRequest request) {
        boolean sanitize = Boolean.TRUE.equals(request.sanitizeOutput());
        return aiGatewayService.streamChatWithSink(request.message(), sanitize)
                .map(chunk -> ServerSentEvent.<String>builder().event("chunk").data(chunk).build())
                .onErrorResume(ex -> Flux.just(
                        ServerSentEvent.<String>builder()
                                .event("error")
                                .data(ex.getMessage() == null ? "流式响应失败" : ex.getMessage())
                                .build()
                ));
    }

    @PostMapping("/realtime/client-secret")
    public RealtimeClientSecretResponse createRealtimeClientSecret(
            @RequestBody(required = false) RealtimeClientSecretRequest request
    ) {
        RealtimeClientSecretRequest safeRequest = request == null
                ? new RealtimeClientSecretRequest(null, null)
                : request;
        return realtimeSessionService.createClientSecret(safeRequest);
    }

    @PostMapping(value = "/interview/turn/stream", produces = MediaType.APPLICATION_NDJSON_VALUE)
    public Flux<InterviewStreamEvent> interviewTurnStream(@Valid @RequestBody InterviewTurnRequest request) {
        return interviewTurnService.handleStream(request);
    }


    @GetMapping("/interview/sessions")
    public List<InterviewSessionSummaryResponse> listInterviewSessions(
            @RequestParam(value = "limit", defaultValue = "20") Integer limit
    ) {
        return interviewSessionStoreService.listSessions(limit == null ? 20 : limit);
    }

    @GetMapping("/interview/sessions/{sessionId}")
    public InterviewSessionDetailResponse getInterviewSession(@PathVariable String sessionId) {
        return interviewSessionStoreService.getSessionDetail(sessionId);
    }
    @PostMapping("/rag/query")
    public RagQueryResponse ragQuery(@Valid @RequestBody RagQueryRequest request) {
        return ragService.ragQuery(request);
    }

    @PostMapping("/rag/documents")
    public RagIngestResponse ingestDocuments(@Valid @RequestBody RagIngestRequest request) {
        return new RagIngestResponse(ragService.ingestDocuments(request));
    }

    @PostMapping(value = "/rag/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public RagUploadResponse uploadRagAssets(@RequestParam("files") List<MultipartFile> files) {
        return ragService.uploadFiles(files);
    }
}
