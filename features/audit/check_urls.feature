Feature: Datasheet URL recovery ladder (jbom audit --check-urls)
  As a hardware developer curating the SPCoast-inventory datasheet library
  I want an opt-in check that walks the URL recovery ladder and proposes
  upgrades as a full-sheet paste
  So that I can find dead/impostor Datasheet URLs and apply fixes myself,
  without jbom ever writing to my inventory or touching the network
  unless I explicitly ask it to

  Background:
    Given a check-urls fixture manifest

  Scenario: --check-urls is off by default; no report or network access occurs
    Given an inventory file "inventory.csv" that contains:
      | RowType | IPN  | Category | Value | Package | Datasheet                                       |
      | ITEM    | R001 | RES      | 10K   | 0603    | https://wmsc.lcsc.com/wmsc/upload/file/r001.pdf |
    When I run "jbom audit inventory.csv"
    Then the command should succeed
    And the output should not contain "URL check complete"

  Scenario: Rung 1 -- a durable wmsc CDN URL fetches a real PDF as-is
    Given the check-urls URL "https://wmsc.lcsc.com/wmsc/upload/file/r001.pdf" resolves to a PDF
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN  | Category | Value | Package | Datasheet                                       |
      | ITEM    | R001 | RES      | 10K   | 0603    | https://wmsc.lcsc.com/wmsc/upload/file/r001.pdf |
    When I run "jbom audit inventory.csv --check-urls"
    Then the command should succeed
    And the output should contain "https://wmsc.lcsc.com/wmsc/upload/file/r001.pdf"
    And the output should contain "1 URL(s) checked, 0 upgrade(s) proposed"

  Scenario: Rung 2 -- an LCSC viewer URL is upgraded via the CDN transform
    Given the check-urls URL "https://www.lcsc.com/datasheet/lcsc_datasheet_2103_WS2812B.pdf" resolves to HTML
    And the check-urls URL "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2103_WS2812B.pdf" resolves to a PDF
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN     | Category | Value    | Package | Datasheet                                                     |
      | ITEM    | LED_001 | LED      | WS2812B  | 5050    | https://www.lcsc.com/datasheet/lcsc_datasheet_2103_WS2812B.pdf |
    When I run "jbom audit inventory.csv --check-urls -o result.csv"
    Then the command should succeed
    And a file named "result.csv" should exist
    And the file "result.csv" should contain "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2103_WS2812B.pdf"
    And the output should contain "1 upgrade(s) proposed"

  Scenario: Rung 3 -- a bare LCSC C-number is upgraded via the product-detail API
    Given the check-urls URL "https://www.lcsc.com/datasheet/C7442870.pdf" resolves to HTML
    And the check-urls LCSC product-detail API for "C7442870" returns durable PDF URL "https://datasheet.lcsc.com/datasheet/pdf/abc123hash.pdf"
    And the check-urls URL "https://datasheet.lcsc.com/datasheet/pdf/abc123hash.pdf" resolves to a PDF
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN     | Category | Value   | Package | Datasheet                                    |
      | ITEM    | CON_001 | CON      | RJ45    | THT     | https://www.lcsc.com/datasheet/C7442870.pdf  |
    When I run "jbom audit inventory.csv --check-urls -o result.csv"
    Then the command should succeed
    And the file "result.csv" should contain "https://datasheet.lcsc.com/datasheet/pdf/abc123hash.pdf"
    And the output should contain "1 upgrade(s) proposed"

  Scenario: Rung 4 -- a manufacturer URL that bot-blocks is reported for manual review, never guessed
    Given the check-urls URL "https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf" resolves to HTML
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN    | Category | Value   | Package | Datasheet                                          |
      | ITEM    | IC_001 | IC       | PCA9685 | TSSOP16 | https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf |
    When I run "jbom audit inventory.csv --check-urls -o result.csv"
    Then the command should succeed
    And the file "result.csv" should contain "https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf"
    And the output should contain "1 need manual review"
    And the output should contain "0 upgrade(s) proposed"

  Scenario: Rung 5 -- a signed/ephemeral URL is reported dead by design and never fetched
    Given an inventory file "inventory.csv" that contains:
      | RowType | IPN    | Category | Value | Package | Datasheet                                                                    |
      | ITEM    | IC_002 | IC       | RELAY | SPDT    | https://jlc-oss.oss-cn-shenzhen.aliyuncs.com/f.pdf?OSSAccessKeyId=a&Signature=b&Expires=1 |
    When I run "jbom audit inventory.csv --check-urls -o result.csv"
    Then the command should succeed
    And the file "result.csv" should contain "https://jlc-oss.oss-cn-shenzhen.aliyuncs.com/f.pdf?OSSAccessKeyId=a&Signature=b&Expires=1"
    And the output should contain "1 dead by design"

  Scenario: Convergence -- Items sharing a Datasheet Name disagree on URL; the working one is proposed
    Given the check-urls URL "https://wmsc.lcsc.com/wmsc/upload/file/uniroyal.pdf" resolves to a PDF
    And the check-urls URL "https://www.lcsc.com/datasheet/lcsc_datasheet_uniroyal_old.pdf" resolves to HTML
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN   | Category | Value | Package | Datasheet                                                        | Datasheet Name              |
      | ITEM    | RES_1 | RES      | 10K   | 0603    | https://wmsc.lcsc.com/wmsc/upload/file/uniroyal.pdf              | Uniroyal-thick-film-series   |
      | ITEM    | RES_2 | RES      | 1K    | 0603    | https://www.lcsc.com/datasheet/lcsc_datasheet_uniroyal_old.pdf   | Uniroyal-thick-film-series   |
    When I run "jbom audit inventory.csv --check-urls -o result.csv"
    Then the command should succeed
    And the file "result.csv" should contain "RES_1"
    And the file "result.csv" should contain "RES_2"
    And the output should contain "2 URL(s) checked"

  Scenario: --check-urls never writes to the source inventory file
    Given the check-urls URL "https://www.lcsc.com/datasheet/lcsc_datasheet_2103_WS2812B.pdf" resolves to HTML
    And the check-urls URL "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2103_WS2812B.pdf" resolves to a PDF
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN     | Category | Value   | Package | Datasheet                                                      |
      | ITEM    | LED_001 | LED      | WS2812B | 5050    | https://www.lcsc.com/datasheet/lcsc_datasheet_2103_WS2812B.pdf |
    When I run "jbom audit inventory.csv --check-urls -o result.csv"
    Then the command should succeed
    And the file "inventory.csv" should contain "https://www.lcsc.com/datasheet/lcsc_datasheet_2103_WS2812B.pdf"

  Scenario: --check-urls rejects project-mode input
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I run "jbom audit . --check-urls"
    Then the command should fail
    And the output should contain "only valid in inventory mode"
