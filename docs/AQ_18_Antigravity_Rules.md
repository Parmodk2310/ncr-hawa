# AQ_18. Rules for Using Antigravity (Gemini 3.8 Flash High)

Status: ACTIVE. The agent is a fast assistant you supervise, not the owner of the project. Tool terms, quotas, models and countries change; **read Google's current terms and pricing pages yourself.** Earlier notes you shared came from secondary reviews.

## Ten rules
1. **No secrets in the project folder.** OpenAQ/FIRMS keys, signing keys, passwords, Play logins stay out. Use environment variables/CI secrets and `.gitignore`. Assume anything the agent can read can leak.
2. **Make it ask before acting.** Every terminal command and file change needs your approval.
3. **Commit before each run; read every diff after.** Work on a branch.
4. **You own the modelling core:** target definition, leakage controls, baselines, evaluation, decision rule. The agent may do scaffolding, ingestion boilerplate, UI screens, tests, CI files.
5. **Never trust a number the agent reports.** Run evaluation yourself, save logs, publish only what you measured.
6. **Check every package it adds:** real name, working version, licence (watch AGPL/non-commercial).
7. **Respect data terms.** The agent must not scrape sites, bypass rate limits, or add data sources without you checking the licence first.
8. **You own the Play and privacy answers.** Fill Data Safety from your own code review.
9. **Keep accounts clean.** Personal Google account, official interface, no third-party logins reusing it.
10. **Log it and say it.** AI Assistance Log (AQ_17) and a README statement.

## Working pattern
- One task card per session (AQ_07). Small tasks.
- Start: "Read AGENTS.md and docs/<doc>. Task: ...". End: commit, log, note what you could not explain and study it.
- Do not paste private or unpublished sensitive material. Check the tool's data-use settings.

## Known limits to plan around (verify each)
Quota and model availability can change; lockouts/suspensions have been reported by some users; security limitations may be acknowledged in terms; eligibility depends on account type, age and country; the agent can invent functions or use outdated Android/Gradle/Python library versions; it cannot do human steps (developer verification, testers, real-phone tests, legal review). Keep all work in Git and have a fallback way to work.

## Never delegate
Choosing the forecast target and defending it; the decision rule and what to claim; what the app collects and what the policy says; signing keys; Play submissions; resume claims.
