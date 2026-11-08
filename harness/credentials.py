"""Read only recognized keys from a local .env; never execute shell syntax."""

import os
from pathlib import Path
import shlex

KEY_NAMES = {"OPENAI_API_KEY", "GEMINI_API_KEY"}


def load_credentials(path: Path) -> dict[str, str]:
    values = {key: os.environ[key] for key in KEY_NAMES if os.environ.get(key)}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            name, separator, raw = line.partition("=")
            name = name.strip()
            if not separator or name not in KEY_NAMES:
                continue
            try:
                parts = shlex.split(raw, comments=True, posix=True)
            except ValueError:
                raise ValueError(f"Invalid quoting for {name} in .env (value suppressed).") from None
            if len(parts) != 1:
                if not parts:
                    continue
                raise ValueError(f"Invalid {name} entry in .env (value suppressed).")
            # The explicitly supplied project .env takes precedence.
            values[name] = parts[0]
    return values
