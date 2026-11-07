@domain:developer-tooling @area:installation @from:dockerfile-hardener/install
Feature: Installing hadofix with the one-line installer
  Lets an operator install the hadofix command with a single piped shell command, using pipx when it is available and falling back to a per-user pip install.

  Background:
    Given the operator runs the one-line installer from the hadofix repository

  @id:developer-tooling.installation.001 @rule:installation.installer.prefers-pipx-falls-back-to-user-pip @inferred @source:install.sh#install.sh
  Scenario Outline: The installer uses pipx when present and otherwise installs for the current user with pip
    Given <tool> is <availability> on the operator's PATH
    When the operator runs the one-line installer
    Then hadofix is installed from the latest main branch of the hadofix repository with <installer>
    And the operator sees "hadofix installed. Run: hadofix --help"

    Examples:
      | tool | availability  | installer          |
      | pipx | available     | pipx install       |
      | pipx | not available | pip install --user |

  @id:developer-tooling.installation.002 @rule:installation.installer.failure-reports-no-success @inferred @source:install.sh#install.sh
  Scenario: A failed install stops the installer without claiming success
    Given the package install step fails, for example because pip is missing or the environment refuses user installs
    When the operator runs the one-line installer
    Then the installer exits with a non-zero status
    And the operator does not see "hadofix installed. Run: hadofix --help"
