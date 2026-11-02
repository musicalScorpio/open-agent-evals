# Security Policy

## Scope

Please report vulnerabilities in the benchmark runner, tool sandbox, authorization enforcement, redaction, secret handling, or result publication process.

Do not include real secrets, personal data, or production credentials in benchmark scenarios, traces, fixtures, or issue reports.

## Reporting

Until a private security-reporting channel is configured for the GitHub repository, do not open a public issue containing exploit details. Contact the repository owner privately and include the minimum information required to reproduce the problem.

## Benchmark safety

Red-team and prompt-injection suites must target isolated fixtures and mock services by default. Tests that can create external side effects require an explicit opt-in execution profile.
