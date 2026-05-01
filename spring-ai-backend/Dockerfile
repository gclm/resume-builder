# author: jf

ARG MAVEN_IMAGE=maven:3.9.9-eclipse-temurin-21
ARG JRE_IMAGE=eclipse-temurin:21-jre-alpine

# 构建阶段使用 Maven 和 JDK 21，保证与 Spring Boot 运行版本一致。
FROM ${MAVEN_IMAGE} AS build

WORKDIR /workspace

COPY pom.xml ./
RUN mvn -B -DskipTests dependency:go-offline

COPY src ./src
RUN mvn -B -DskipTests package

# 运行阶段只保留 JRE 和打包产物，减少最终镜像体积。
FROM ${JRE_IMAGE}

WORKDIR /app

ENV SERVER_PORT=8999

COPY --from=build /workspace/target/*.jar /app/app.jar

EXPOSE 8999

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 CMD wget -qO- "http://127.0.0.1:${SERVER_PORT}/health" || exit 1

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
