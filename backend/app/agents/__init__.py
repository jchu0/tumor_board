"""Agentic layer — surfaces nuance the deterministic path can't see.

The deterministic ingestion maps *coded* fields. Clinical nuance lives in prose
(transcript, longitudinal summary, notes): performance status implied by casual
speech, an uncoded comorbidity, an implicit goals-of-care concern. Agents read
that text and emit *candidate* inferences — always in a separate channel from
grounded data, always pointing at a verbatim source span.

Agent template (every agent here follows it):
  1. a structured-output SCHEMA (its own file) — forces consistent output;
  2. a SYSTEM prompt + a forced structured-output tool;
  3. a run function returning the validated object, with graceful degradation
     (any failure — including no API key — returns an empty/ skipped result so
     the deterministic pipeline still produces a baseline);
  4. a deterministic VERIFIER that grounds every claim against the source text.
"""
