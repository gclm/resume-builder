// author: jf
package com.resumebuilder.springaibackend.embedding;

import java.util.ArrayList;
import java.util.List;
import org.springframework.ai.document.Document;
import org.springframework.ai.embedding.Embedding;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.embedding.EmbeddingRequest;
import org.springframework.ai.embedding.EmbeddingResponse;

public class SpringAiEmbeddingModelAdapter implements EmbeddingModel {

    private final EmbeddingClient embeddingClient;
    private final int configuredDimensions;
    private volatile Integer cachedDimensions;

    public SpringAiEmbeddingModelAdapter(EmbeddingClient embeddingClient, int configuredDimensions) {
        this.embeddingClient = embeddingClient;
        this.configuredDimensions = Math.max(0, configuredDimensions);
    }

    @Override
    public EmbeddingResponse call(EmbeddingRequest request) {
        List<String> texts = request == null || request.getInstructions() == null
                ? List.of()
                : request.getInstructions();
        List<float[]> embeddings = embed(texts);
        List<Embedding> results = new ArrayList<>(embeddings.size());
        for (int i = 0; i < embeddings.size(); i++) {
            results.add(new Embedding(embeddings.get(i), i));
        }
        return new EmbeddingResponse(results);
    }

    @Override
    public float[] embed(Document document) {
        return embed(document == null ? "" : document.getText());
    }

    @Override
    public float[] embed(String text) {
        List<float[]> embeddings = embed(List.of(text == null ? "" : text));
        return embeddings.isEmpty() ? new float[0] : embeddings.get(0);
    }

    @Override
    public List<float[]> embed(List<String> texts) {
        List<String> safeTexts = texts == null ? List.of() : texts;
        if (safeTexts.isEmpty()) {
            return List.of();
        }
        List<List<Double>> rawEmbeddings = embeddingClient.embedTexts(safeTexts);
        if (rawEmbeddings.size() != safeTexts.size()) {
            throw new IllegalStateException("Embedding 数量与文本数量不一致");
        }
        List<float[]> convertedEmbeddings = new ArrayList<>(rawEmbeddings.size());
        for (List<Double> rawEmbedding : rawEmbeddings) {
            float[] embedding = toFloatArray(rawEmbedding);
            if (embedding.length > 0) {
                cachedDimensions = embedding.length;
            }
            convertedEmbeddings.add(embedding);
        }
        return convertedEmbeddings;
    }

    @Override
    public int dimensions() {
        Integer dimensions = cachedDimensions;
        if (dimensions != null && dimensions > 0) {
            return dimensions;
        }
        if (configuredDimensions > 0) {
            return configuredDimensions;
        }
        throw new IllegalStateException("Embedding 向量维度未配置且无法根据模型推断，请设置 EMBEDDING_DIMENSIONS 后重启");
    }

    private static float[] toFloatArray(List<Double> values) {
        List<Double> safeValues = values == null ? List.of() : values;
        float[] floats = new float[safeValues.size()];
        for (int i = 0; i < safeValues.size(); i++) {
            Double value = safeValues.get(i);
            floats[i] = value == null ? 0.0F : value.floatValue();
        }
        return floats;
    }
}
