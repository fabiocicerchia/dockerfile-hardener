from dockerfile_hardener import harden


def test_pins_untagged_base():
    out, changes = harden('FROM ubuntu\nRUN echo hi\nCMD ["true"]\n')
    assert "ubuntu:latest  # TODO: pin a real version" in out
    assert any(r == "pin-base" for r, _ in changes)


def test_package_manager_flags_added():
    out, _ = harden("FROM alpine:3.22\nRUN apk add curl\nRUN pip install flask\n")
    assert "apk add --no-cache curl" in out
    assert "pip install --no-cache-dir flask" in out


def test_apt_gets_cleanup_and_no_recommends():
    out, _ = harden(
        "FROM debian:bookworm-slim\nRUN apt-get update && apt-get install -y curl\n"
    )
    assert "--no-install-recommends" in out
    assert "rm -rf /var/lib/apt/lists/*" in out


def test_user_inserted_before_entrypoint_only_when_missing():
    out, _ = harden('FROM alpine:3.22\nENTRYPOINT ["app"]\n')
    lines = out.splitlines()
    assert lines.index(
        "USER 10001  # TODO: create this user in an earlier layer if needed"
    ) < lines.index('ENTRYPOINT ["app"]')
    again, changes = harden(out)
    assert not any(r == "non-root" for r, _ in changes)


def test_healthcheck_hint_when_expose_present():
    out, _ = harden('FROM alpine:3.22\nEXPOSE 8080\nCMD ["app"]\n')
    assert "HEALTHCHECK" in out


def test_idempotent():
    src = 'FROM alpine:3.22\nRUN apk add curl\nCMD ["app"]\n'
    once, _ = harden(src)
    twice, _ = harden(once)
    assert once == twice


def test_multi_stage_hint_when_single_stage_has_build_deps():
    out, changes = harden(
        'FROM alpine:3.22\nRUN apk add --no-cache build-essential\nCMD ["app"]\n'
    )
    assert "multi-stage build" in out
    assert any(r == "multi-stage" for r, _ in changes)


def test_multi_stage_hint_skipped_without_build_deps():
    out, changes = harden('FROM alpine:3.22\nRUN apk add --no-cache curl\nCMD ["app"]\n')
    assert "multi-stage" not in out
    assert not any(r == "multi-stage" for r, _ in changes)


def test_multi_stage_hint_skipped_when_already_multi_stage():
    src = (
        "FROM alpine:3.22 AS builder\n"
        "RUN apk add --no-cache build-essential\n"
        "FROM alpine:3.22\n"
        'CMD ["app"]\n'
    )
    out, changes = harden(src)
    assert "multi-stage build" not in out
    assert not any(r == "multi-stage" for r, _ in changes)
