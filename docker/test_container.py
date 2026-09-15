#!/usr/bin/env python3
"""Exercise a built image on an isolated network, including a separate client."""

import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid


def docker(*args, check=True):
    return subprocess.run(
        ["docker", *args], check=check, text=True, capture_output=True
    )


def wait_ready(container, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = json.loads(docker("inspect", container).stdout)[0]["State"]
        if not state["Running"]:
            raise AssertionError("LanguageTool exited during startup")
        if state.get("Health", {}).get("Status") == "healthy":
            return
        time.sleep(2)
    raise AssertionError("LanguageTool did not become healthy")


def main():
    image = sys.argv[1]
    token = uuid.uuid4().hex[:12]
    network = f"lt-contract-{token}"
    container = f"lt-contract-server-{token}"
    docker("network", "create", network)
    try:
        docker(
            "run", "--detach", "--name", container, "--network", network,
            "--network-alias", "grammar", "--memory", "1g", "--cpus", "2",
            "--publish", "127.0.0.1::8081", image,
        )
        wait_ready(container)
        metadata = json.loads(docker("inspect", container).stdout)[0]
        assert metadata["Config"]["User"] == "10001:10001"
        assert metadata["Config"]["Labels"].get("org.opencontainers.image.revision")
        classpath = "/opt/languagetool/health:/opt/languagetool/libs/*"
        for language in ("en-AU", "es", "ca", "pt-PT"):
            docker(
                "run", "--rm", "--network", network,
                "--env", f"RAVENOUS_INPUT_LANGUAGE={language}",
                "--entrypoint", "java", image, "-cp", classpath,
                "Healthcheck", "http://grammar:8081",
            )
        invalid = docker(
            "run", "--rm", "--network", network,
            "--env", "RAVENOUS_INPUT_LANGUAGE=invalid-private-value",
            "--entrypoint", "java", image, "-cp", classpath,
            "Healthcheck", "http://grammar:8081", check=False,
        )
        assert invalid.returncode == 1
        assert not invalid.stdout and not invalid.stderr

        # A correctable sentence proves the endpoint actually loads language rules.
        port = metadata["NetworkSettings"]["Ports"]["8081/tcp"][0]["HostPort"]
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v2/languages", timeout=15
        ) as response:
            assert {item["code"] for item in json.load(response)} == {
                "en", "es", "ca", "pt"
            }
        sentinel = f"private-request-{token}"
        body = urllib.parse.urlencode({
            "language": "en-AU", "text": f"This are a test. {sentinel}"
        }).encode()
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v2/check", data=body, timeout=15
        ) as response:
            assert json.load(response)["matches"]
        logs = docker("logs", container)
        assert sentinel not in logs.stdout + logs.stderr
        assert "invalid-private-value" not in logs.stdout + logs.stderr

        docker("restart", container)
        wait_ready(container)
        print("Passed: readiness, cross-container HTTP, languages, privacy, restart")
    finally:
        docker("rm", "--force", container, check=False)
        docker("network", "rm", network, check=False)


if __name__ == "__main__":
    main()
