# Ravenous LanguageTool service

The image compiles this checkout with Java 17. The runtime includes English,
Spanish, Catalan, and Portuguese and their required dependencies, matching the
previous Ravenous package. The upstream Maven reactor builds all languages because
the server and its shared test fixtures depend on them; unselected language jars
are excluded from the final image. Maven dependency versions remain in the
upstream POMs. Java and Maven image references are pinned by digest.

Build from the repository root:

```sh
docker build --build-arg SOURCE_REVISION="$(git rev-parse HEAD)" \
  -t "ravenous-languagetool:$(git rev-parse HEAD)" .
```

The HTTP server binds port 8081 on all container interfaces. Use Docker service
DNS on one machine; for remote consumers explicitly publish a private interface
and port, and allow access only from the application hosts. Do not publish the
unauthenticated service directly to the Internet. Ravenous configures placement,
port publication, and the URL used by Open WebUI.

Set `RAVENOUS_INPUT_LANGUAGE` to the same language as Open WebUI (default `en-AU`).
The health check sends synthetic text to `/v2/check`, requires a valid matches
array, and warms that language. Its 180-second startup allowance permits the cold
model load. Open WebUI also checks its own configured endpoint, including remote
endpoints, before serving correction requests.

The service runs as UID/GID 10001, without persistent data. Java uses at most 70%
of the container memory limit; configure at least 1 GiB for these language modules
and increase it after workload measurements. Override server bounds by mounting a
read-only file at `/opt/languagetool/server.properties`. Request and exception logs
are suppressed because upstream messages can contain client parameters. Health
checks produce no response or exception output. Inspect health status and HTTP
responses for diagnostics.

Run all source tests with `mvn --batch-mode --no-transfer-progress -pl
languagetool-server -am test`. The Docker target `test` runs the upstream HTTP
server and configuration tests without requiring Maven/Java on the host:

```sh
docker build --target test .
```

Run the container contract test after building:

```sh
python3 docker/test_container.py "ravenous-languagetool:$(git rev-parse HEAD)"
```

The test starts only temporary containers on a temporary Docker network. It checks
cross-container requests, exactly the four packaged languages, invalid language readiness,
non-root execution, restart recovery, and that request text stays out of logs.
It limits the server to 1 GiB of memory. Existing stacks, networks, and data are
never modified.

Validation on 2026-09-16, based on upstream commit
`fc5fd4f3c44082ecbe1b5a266144a5dcca1da20e` (6.9-SNAPSHOT): the source-built image
passed the container contract test. The Docker `test` target ran 12 upstream HTTP
server/configuration tests, with no failures or errors and two tests skipped by
upstream. The full upstream multilingual test suite has not been run.
