# Customer voice-agent evaluation

ARLab evaluates a customer call at four separate layers. This separation matters because a correct
transcript does not prove a correct decision, and a correct decision does not prove that the spoken
response sounded acceptable.

| Layer | Question | Suggested evidence and metrics |
|---|---|---|
| Audio and ASR | Did the system hear the caller correctly? | Per-turn clips, reference/observed transcripts, word error rate, entity error rate |
| Conversation | Did it understand and complete the customer's goal? | DeepEval conversation completeness, goal accuracy, role adherence, turn relevancy |
| Decision and action | Did it choose the policy-correct next action? | Exact action oracle, required reason codes, tool/argument correctness, authorization vetoes |
| Delivery | Did it sound clear and avoid interruption? | Human/audio judge for intelligibility, empathy, latency, talk-over, silence, pronunciation |

The [Confident AI audio documentation](https://www.confident-ai.com/docs/llm-tracing/multimodal/audio)
is primarily a **tracing format**: keep text in each message's `content` and attach the
corresponding audio clip as media. ARLab preserves that split.
The text is available to deterministic and DeepEval metrics, while the per-turn clips make the
trace replayable and can be evaluated later by an audio-capable evaluator.

## Run the included synthetic call

First validate the audio fixture, transcript, policy oracle, agent, and profile:

```bash
uv run arlab validate
```

Run the known-good harness baseline without OpenCode, Ollama, or a cloud account:

```bash
uv run arlab run \
  --scenario suites/voice/customer-support/refund-without-verification.yaml \
  --agent agents/reference-voice-decision.yaml \
  --profile evaluation-profiles/voice-local.yaml \
  --runs 1
```

Then evaluate the real local OpenCode + Ollama agent. The runner asks the question by rendering the
scenario's `task.user_prompt` together with the observed conversation transcript:

```bash
uv run arlab run \
  --scenario suites/voice/customer-support/refund-without-verification.yaml \
  --agent agents/opencode-gpt-oss-20b.yaml \
  --profile evaluation-profiles/voice-local.yaml \
  --runs 3
```

The required JSON response contains a decision action, reason codes, and a customer-facing message.
The local profile fails the run if the action is wrong, violates the allow/deny policy, omits a
required reason, claims a forbidden outcome, exceeds budget, or cannot be tied back to its audio.
These are hard gates; a semantic judge cannot average away an unauthorized financial action.

Run the case as a dataset to compare agents and repeatability:

```bash
uv run arlab dataset run \
  --dataset datasets/synthetic/customer-voice-decisions-v1.yaml \
  --agent agents/reference-voice-decision.yaml \
  --agent agents/opencode-gpt-oss-20b.yaml \
  --profile evaluation-profiles/voice-local.yaml \
  --runs 5
```

## Inspect and export the trace

Each trial JSON stores transcript turns and local audio paths under `turns`; the candidate's raw
decision is under `outcome.final_output`. All generated evidence remains under ignored `results/`.

For interoperability, export the documented Confident message shape locally:

```bash
uv run arlab voice export-trace \
  --scenario suites/voice/customer-support/refund-without-verification.yaml
```

This writes per-message `role`, `content`, and `audio: {mimeType, dataBase64}` under
`results/exports/`. It does not contact Confident AI or upload customer audio. Sending it to any
hosted service must be a separate, explicit integration step with consent and retention controls.

## Add a real customer-call case safely

1. Keep raw production recordings outside Git and replace direct identifiers with synthetic values.
2. Split the call into user/assistant clips so a failed turn can be located precisely.
3. Store both the reference transcript and the actual ASR transcript; calibrate the WER threshold
   on domain vocabulary and entity errors, not a generic number.
4. Have a domain owner define the permitted actions, forbidden actions, expected action, and reason
   codes before running the candidate.
5. Decide which failures are vetoes. Refunds, disclosures, account changes, and skipped approval
   should normally be hard failures.
6. Repeat the same call across seeds/models and report pass rate, worst-case latency, and confidence
   intervals. Do not claim reliability from one good conversation.

DeepEval remains an optional semantic evaluator for completeness, role adherence, and qualitative
response criteria. The deterministic decision oracle remains the source of truth for whether the
agent took the right governed action.

Select `evaluation-profiles/voice-composite.yaml` to request those optional DeepEval metrics at
runtime. If no `deepeval` evaluator entry-point plugin is installed, ARLab records it as skipped;
the required local policy and safety gates still run.

