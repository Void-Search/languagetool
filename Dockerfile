# syntax=docker/dockerfile:1
FROM maven:3.9-eclipse-temurin-17@sha256:880934ae394bf91bc3e57d573e4fc04774f064f3c4df7ccd7cc10b3b126737bf AS build
WORKDIR /src
COPY . .
# Compile the upstream reactor (including its shared test fixtures); package only
# the languages selected by docker/pom.xml in the runtime image.
RUN --mount=type=cache,target=/root/.m2 \
    mvn --batch-mode --no-transfer-progress -pl languagetool-server -am \
        -DskipTests -Dmaven.gitcommitid.skip=true install \
    && mvn --batch-mode --no-transfer-progress -f docker/pom.xml \
        org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies \
        -DincludeScope=runtime -DoutputDirectory=/opt/languagetool/libs \
    && javac --release 17 -cp '/opt/languagetool/libs/*' \
        -d /opt/languagetool/health docker/Healthcheck.java

FROM build AS test
RUN --mount=type=cache,target=/root/.m2 \
    mvn --batch-mode --no-transfer-progress -pl languagetool-server -am \
        -Dmaven.gitcommitid.skip=true -Dtest=HTTPServerConfigTest,HTTPServerTest \
        -Dsurefire.failIfNoSpecifiedTests=false test

FROM eclipse-temurin:17-jre-jammy@sha256:ec72ba5962b45ae4e7f96bfb5ebf6eeb34a488b967f937c8e14f0aaec688954f
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/Void-Search/languagetool" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
WORKDIR /opt/languagetool
COPY --from=build /opt/languagetool /opt/languagetool
COPY docker/server.properties docker/logback.xml ./
ENV RAVENOUS_INPUT_LANGUAGE=en-AU
EXPOSE 8081
USER 10001:10001
HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=3 \
    CMD ["java", "-Xms16m", "-Xmx64m", "-cp", "/opt/languagetool/health:/opt/languagetool/libs/*", "Healthcheck"]
ENTRYPOINT ["java", "-Xms128m", "-XX:MaxRAMPercentage=70.0", "-XX:+ExitOnOutOfMemoryError", "-Dlogback.configurationFile=/opt/languagetool/logback.xml", "-cp", "/opt/languagetool/libs/*", "org.languagetool.server.HTTPServer", "--public", "--port", "8081", "--notLogIP", "--config", "/opt/languagetool/server.properties"]
