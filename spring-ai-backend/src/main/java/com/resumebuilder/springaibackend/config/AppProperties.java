// author: jf
package com.resumebuilder.springaibackend.config;

import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private final List<String> corsAllowedOrigins = new ArrayList<>(List.of("http://localhost:5173"));

    private int ragTopK = 5;

    private int ragChunkSize = 700;

    private int ragChunkOverlap = 70;

    private int ragMaxFileSizeMb = 10;

    private int interviewRagTopK = 4;

    private double interviewRagSimilarityThreshold = 0.5D;

    private double interviewRagTimeoutSeconds = 3.0D;

    public List<String> getCorsAllowedOrigins() {
        return corsAllowedOrigins;
    }

    public int getRagTopK() {
        return ragTopK;
    }

    public void setRagTopK(int ragTopK) {
        this.ragTopK = ragTopK;
    }

    public int getRagChunkSize() {
        return ragChunkSize;
    }

    public void setRagChunkSize(int ragChunkSize) {
        this.ragChunkSize = ragChunkSize;
    }

    public int getRagChunkOverlap() {
        return ragChunkOverlap;
    }

    public void setRagChunkOverlap(int ragChunkOverlap) {
        this.ragChunkOverlap = ragChunkOverlap;
    }

    public int getRagMaxFileSizeMb() {
        return ragMaxFileSizeMb;
    }

    public void setRagMaxFileSizeMb(int ragMaxFileSizeMb) {
        this.ragMaxFileSizeMb = ragMaxFileSizeMb;
    }

    public int getInterviewRagTopK() {
        return interviewRagTopK;
    }

    public void setInterviewRagTopK(int interviewRagTopK) {
        this.interviewRagTopK = interviewRagTopK;
    }

    public double getInterviewRagSimilarityThreshold() {
        return interviewRagSimilarityThreshold;
    }

    public void setInterviewRagSimilarityThreshold(double interviewRagSimilarityThreshold) {
        this.interviewRagSimilarityThreshold = interviewRagSimilarityThreshold;
    }

    public double getInterviewRagTimeoutSeconds() {
        return interviewRagTimeoutSeconds;
    }

    public void setInterviewRagTimeoutSeconds(double interviewRagTimeoutSeconds) {
        this.interviewRagTimeoutSeconds = interviewRagTimeoutSeconds;
    }
}
