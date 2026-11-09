# Copilot instructions

- Keep the demo runnable with Python 3.12 and the standard library except for the pinned Microsoft Foundry Anthropic SDK.
- Keep Foundry credentials in environment variables or platform secrets; never add credentials to source, logs, or examples.
- Keep the chat route behind demo authentication; leave `/healthz` available for platform probes.
- Use `python -m unittest discover -s app/tests -v` to validate changes.
- Preserve the `/healthz` endpoint and the Claude Sonnet 5.5 `max` effort configuration.
