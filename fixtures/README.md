# Fixtures

Fixtures are deterministic external state used by scenarios: tool responses, files, database rows, identities, permissions, and injected errors.

Planned layout:

```text
fixtures/
├── tools/
│   └── <tool-name>/
├── repositories/
│   └── <fixture-repository>/
├── identities/
└── injections/
```

Scenarios reference fixture identifiers and versions rather than live services. The Step 1 schema revision will add an explicit fixture binding before the weather scenario becomes executable.

