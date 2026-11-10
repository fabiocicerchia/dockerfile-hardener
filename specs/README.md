# Specifications of dockerfile-hardener

What this code does, one atomic Gherkin scenario per behaviour, read from the code by code-atlas.
Tags: `@verified` a test asserts it · `@inferred` read from the code only · `@gap` an entry point no test covers · `@human` written or amended by a person, never rewritten.

## Build hygiene fixes
Rewrites that make RUN steps safer and images leaner.

- **Apt cache cleanup**: [Build hygiene fixes](build-hygiene/apt-cleanup/build-hygiene-fixes.feature) (3)

## Developer tooling
Installing hadofix and the tasks used to build, test and lint it.

- **Installation**: [Installing hadofix with the one-line installer](developer-tooling/installation/one-line-installer.feature) (2)

## Finding intake
How hadofix gets hadolint's findings and decides which ones to act on.

- **Running hadolint**: [Running hadolint for findings](finding-intake/hadolint-run/running-hadolint.feature) (2)
- **Findings from stdin**: [Supplying hadolint findings](finding-intake/stdin-findings/supplying-findings.feature) (2)

## Fix results and reporting
What the user sees and gets after a run: the diff, the explanations, the leftovers.

- **Command line and exit codes**: [Gating CI on hadofix's exit status](fix-output/cli-exit/cli-exit-codes.feature) (2)
- **Diff and write-back**: [Reviewing and applying fixes](fix-output/diff-and-write/diff-and-write.feature) (4)
- **Run report**: [Reporting what was fixed and what is left](fix-output/report/run-report.feature) (2)
- **Rule selection and idempotence**: [Letting hadolint decide what gets fixed](fix-output/rule-config/rule-selection.feature) (1)

## Image and package pinning
Making builds reproducible by pinning base images and installed packages from evidence.

- **Base image pinning**: [Pinning base images](image-pinning/base-image-pin/base-image-pinning.feature) (2)
- **Registry digest lookup**: [Pinning base images to Docker Hub digests](image-pinning/digest-lookup/docker-hub-digest-lookup.feature) (3)
- **OS package pinning**: [Pinning package versions](image-pinning/os-package-pin/package-version-pinning.feature) (3)

## Container runtime hardening
Fixes and checks for how the container starts and which user it runs as.

- **Entrypoint script checks**: [Checking that signals reach the application](runtime-hardening/entrypoint-scripts/signal-and-pid1-checks.feature) (3)
- **Exec-form commands**: [Converting commands to exec form](runtime-hardening/exec-form/exec-form-commands.feature) (2)
- **Non-root user**: [Running the image as a non-root user](runtime-hardening/non-root-user/non-root-user.feature) (3)
