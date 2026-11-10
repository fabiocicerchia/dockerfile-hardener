@domain:documentation-site @area:site-theme @from:stylesheets/extra
Feature: Branding the documentation site
  Gives readers of the hadofix docs and splash page one recognisable, legible look in light and dark mode without the site calling out to third parties.

  Background:
    Given the hadofix documentation site and its splash page are published

  @id:docs.documentation-site.site-theme.003 @rule:docs.theme.no-third-party-requests @inferred @source:docs/stylesheets/extra.css#:root
  Scenario: The docs theme loads no web fonts or third-party assets
    Given the reader's browser blocks or has no access to external hosts
    When the reader opens any docs page
    Then text renders in the operating system's own sans-serif font
    And code renders in the operating system's own monospace font
    And no font or stylesheet is fetched from a third-party host

  @id:docs.documentation-site.site-theme.004 @rule:docs.theme.no-placeholder-logo @inferred @source:docs/stylesheets/extra.css#.md-header__button.md-logo
  Scenario: The docs header shows no stand-in logo
    Given the project has no logo configured
    When the reader views the docs header and navigation drawer
    Then no logo icon is shown beside the site name
    And the generic book icon Material would otherwise substitute does not appear
