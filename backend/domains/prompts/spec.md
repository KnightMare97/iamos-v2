# Prompt Template Variables Specification

## System Injected Variables
The orchestrator context engine resolves and interpolates these exact variables before dispatching payloads to the AI Router:

- `{brand_voice}` — Text block defining client tone.
- `{caption_language}` — ISO 639-1 code, e.g. "fa" for Farsi, "en" for English. Dictates the core text generation alignment and layout script.
- `{operator_notes}` — The top 5 high-signal out-of-band scratchpad records from human management logs.
- `{shared_calendar_events}` — The aggregated national or seasonal holidays active during the scheduled slots window.
