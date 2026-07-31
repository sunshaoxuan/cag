# Browser verification

Date: 2026-07-31

Target: `http://127.0.0.1:5173/operations`

Browser: Codex in-app browser

## Verified

* header displays `One Agent Gateway v0.22.0`;
* summary dashboard displays `方案待修订`;
* `OI-6B26534BF5` displays `Agent 与人工协作`, 88 percent confidence;
* issue detail displays `审核决策摘要`;
* problem, impact, root cause and improvement goal are first-class sections;
* five proposed improvements and eight blocking findings are visible;
* approval button count is zero for the blocked issue;
* `重新规划与 Review` button count is one;
* four versioned artifacts and the complete timeline are collapsed by default;
* timeline expands and collapses successfully;
* no horizontal page overflow was detected;
* browser console contained no warning or error records.

## Screenshots

* `operations-center-decision-brief.png`
* `operations-center-issue-detail.png`
* `operations-center-production.png`
