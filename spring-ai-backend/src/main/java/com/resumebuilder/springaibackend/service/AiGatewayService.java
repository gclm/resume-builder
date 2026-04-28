// author: jf
package com.resumebuilder.springaibackend.service;

import com.resumebuilder.springaibackend.cleaner.ResumeMarkdownCleaner;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Service;
import reactor.core.Disposable;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;

@Service
public class AiGatewayService {

    private final ChatClient chatClient;
    private final ResumeMarkdownCleaner resumeMarkdownCleaner;

    public AiGatewayService(
            ChatClient chatClient,
            ResumeMarkdownCleaner resumeMarkdownCleaner
    ) {
        this.chatClient = chatClient;
        this.resumeMarkdownCleaner = resumeMarkdownCleaner;
    }

    public String chat(String message) {
        return chat(message, false);
    }

    public String chat(String message, boolean sanitizeOutput) {
        String content = chatClient.prompt().user(message.trim()).call().content();
        String safe = resumeMarkdownCleaner.safeContent(content);
        return sanitizeOutput ? resumeMarkdownCleaner.sanitizeResumeMarkdown(safe) : safe;
    }

    public Flux<String> streamChat(String message) {
        return chatClient.prompt().user(message.trim()).stream().content();
    }

    public Flux<String> streamChatWithSink(String message) {
        return streamChatWithSink(message, false);
    }

    public Flux<String> streamChatWithSink(String message, boolean sanitizeOutput) {
        Sinks.Many<String> sink = Sinks.many().unicast().onBackpressureBuffer();

        if (!sanitizeOutput) {
            Disposable disposable = chatClient.prompt()
                    .user(message.trim())
                    .stream()
                    .content()
                    .subscribe(
                            sink::tryEmitNext,
                            sink::tryEmitError,
                            sink::tryEmitComplete
                    );
            return sink.asFlux().doFinally(signalType -> disposable.dispose());
        }

        StringBuilder rawBuffer = new StringBuilder();
        int[] emittedLength = {0};

        Disposable disposable = chatClient.prompt()
                .user(message.trim())
                .stream()
                .content()
                .subscribe(
                        chunk -> {
                            rawBuffer.append(chunk);
                            String sanitized = resumeMarkdownCleaner.sanitizeResumeMarkdown(rawBuffer.toString());
                            int stableEnd = sanitized.lastIndexOf('\n');
                            if (stableEnd < 0) {
                                return;
                            }
                            int emitUntil = stableEnd + 1;
                            if (emitUntil > emittedLength[0]) {
                                sink.tryEmitNext(sanitized.substring(emittedLength[0], emitUntil));
                                emittedLength[0] = emitUntil;
                            }
                        },
                        sink::tryEmitError,
                        () -> {
                            String sanitized = resumeMarkdownCleaner.sanitizeResumeMarkdown(rawBuffer.toString());
                            if (sanitized.length() > emittedLength[0]) {
                                sink.tryEmitNext(sanitized.substring(emittedLength[0]));
                            }
                            sink.tryEmitComplete();
                        }
        );
        return sink.asFlux().doFinally(signalType -> disposable.dispose());
    }

}
