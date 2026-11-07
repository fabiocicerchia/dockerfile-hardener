@domain:documentation-site @area:site-theme @from:stylesheets/extra
Feature: Branding the documentation site
  Gives readers of the hadofix docs and splash page one recognisable, legible look in light and dark mode without the site calling out to third parties.

  Background:
    Given the hadofix documentation site and its splash page are published

  @id:docs.documentation-site.site-theme.001 @rule:docs.theme.shared-accent-palette @inferred @source:docs/stylesheets/extra.css#:root
  Scenario: The docs and the splash page share one orange-red accent palette
    Given the site's accent pair is orange #fb923c and red #ef4444
    When a reader opens the splash page and then the rendered docs
    Then the splash headline and install button use an orange-to-red gradient
    And the docs header, navigation chrome and primary colour use red #ef4444
    And interactive accents in the docs use orange #fb923c

  @id:docs.documentation-site.site-theme.002 @rule:docs.theme.links-legible-in-both-schemes @inferred @source:docs/stylesheets/extra.css#[data-md-color-scheme="slate"]
  Scenario Outline: Links stay legible in both light and dark mode
    Given the reader's colour scheme is <scheme>
    When the reader views a docs page containing links
    Then links are shown in <link colour>
    And the page background is <background>

    Examples:
      | scheme | link colour    | background         |
      | light  | red #ef4444    | white              |
      | dark   | orange #fb923c | near-black #0b0f1a |

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
