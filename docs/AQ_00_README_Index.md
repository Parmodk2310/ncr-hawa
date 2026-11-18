# AQ_00. Index: Delhi-NCR Air Quality Forecast App

Working name: **NCR Hawa** (rename freely; keep "official", "CPCB", "government" out of the name).
One line: forecasts the air quality category for Delhi-NCR for the next 24 and 48 hours, compared honestly against simple baselines, shown on a web page and an Android app with a plain health note. No accounts, no ads.

Status of all documents: DRAFT v0.1, written 2026-11-15. Items marked **[VERIFIED 2026-11-15]** were checked in web sources on that date (some secondary). **[VERIFY]** means check yourself before relying on it.

## How to use
1. Read in order. 2. Put `AQ_AGENTS.md` in the repo root as `AGENTS.md`. 3. Give Antigravity ONE task at a time from `AQ_07`. 4. Update the Status line of any doc you change.

## Files
| File | Contents |
|------|----------|
| AQ_00_README_Index.md | This index and golden rules |
| AQ_01_Research_and_Idea.md | Problem statement, scope, data-source verification, competitors to check |
| AQ_02_PRD.md | Requirements, cut line |
| AQ_03_Technical_Architecture.md | System design, data flow, decisions |
| AQ_04_Phase_Plan.md | Dated plan with gates |
| AQ_05_Design_Document.md | Web page and app design, health note |
| AQ_06_Engineering_Standards.md | Code, git, reproducibility |
| AQ_07_Task_Breakdown_and_Backlog.md | Task rules and starting backlog |
| AQ_08_Test_and_QA_Plan.md | Tests, forecast evaluation, field checks |
| AQ_09_Security_Review_Checklist.md | Security and privacy checks |
| AQ_10_Release_and_Operations_Runbook.md | Release, rollback, monitoring, incident steps |
| AQ_11_Data_Plan_and_Datasheet.md | Sources, licence record, datasheet, labelling/QC rules |
| AQ_12_Model_and_Evaluation_Plan.md | Baselines, metrics, experiment log, model card, registry, retraining, monitoring |
| AQ_13_API_and_Database_Spec.md | Static JSON API and storage schema |
| AQ_14_Risk_Register.md | Risks and mitigations |
| AQ_15_Playstore_Launch_Pack.md | 45-item tracker, store listing, declarations, closed test |
| AQ_16_Legal_and_Privacy_Pack.md | Privacy policy, terms, disclaimers, retention, licences |
| AQ_17_Admin_Templates.md | README, test report, changelog, AI assistance log |
| AQ_18_Antigravity_Rules.md | Rules for the coding agent |
| AQ_AGENTS.md | Copy to repo root as AGENTS.md |

## Golden rules
1. Every number in README, store listing and resume comes from a script you ran.
2. Honesty is the product: always show the baseline next to the model. If the model does not beat the baseline, say so.
3. Data licences decide what you may publish. Check before you build around a source.
4. No personal data collection in MVP. Fewer promises, fewer legal problems.
5. The app is an independent information tool, not an official service and not medical advice.
