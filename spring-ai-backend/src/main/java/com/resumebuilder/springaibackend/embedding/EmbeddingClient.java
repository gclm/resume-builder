// author: jf
package com.resumebuilder.springaibackend.embedding;

import java.util.List;

public interface EmbeddingClient {

    String getModelName();

    List<List<Double>> embedTexts(List<String> texts);
}
