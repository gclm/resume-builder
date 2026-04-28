// author: jf
package com.resumebuilder.springaibackend.config;

import javax.sql.DataSource;

import com.resumebuilder.springaibackend.embedding.EmbeddingService;
import com.resumebuilder.springaibackend.embedding.SpringAiEmbeddingModelAdapter;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.ai.vectorstore.pgvector.PgVectorStore;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

@Configuration
public class PgVectorConfig {

    private static final String RAG_VECTOR_TABLE_NAME = "rag_document_chunks";

    @Bean(name = "pgVectorDataSource")
    DataSource pgVectorDataSource(PgVectorProperties properties) {
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setDriverClassName(properties.getDriverClassName());
        dataSource.setJdbcUrl(properties.getUrl());
        dataSource.setUsername(properties.getUsername());
        dataSource.setPassword(properties.getPassword());
        dataSource.setConnectionTimeout(Math.max(1, properties.getConnectTimeoutSeconds()) * 1000L);
        return dataSource;
    }

    @Bean(name = "pgVectorJdbcTemplate")
    JdbcTemplate pgVectorJdbcTemplate(@Qualifier("pgVectorDataSource") DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }

    @Bean(name = "ragEmbeddingModel")
    EmbeddingModel ragEmbeddingModel(EmbeddingService embeddingService) {
        return new SpringAiEmbeddingModelAdapter(embeddingService, embeddingService.getDimensions());
    }

    @Bean(name = "ragVectorStore")
    VectorStore ragVectorStore(
            @Qualifier("pgVectorJdbcTemplate") JdbcTemplate jdbcTemplate,
            @Qualifier("ragEmbeddingModel") EmbeddingModel embeddingModel
    ) {
        return PgVectorStore.builder(jdbcTemplate, embeddingModel)
                .vectorTableName(RAG_VECTOR_TABLE_NAME)
                .idType(PgVectorStore.PgIdType.TEXT)
                .distanceType(PgVectorStore.PgDistanceType.COSINE_DISTANCE)
                .indexType(PgVectorStore.PgIndexType.NONE)
                .initializeSchema(false)
                .vectorTableValidationsEnabled(false)
                .build();
    }
}
