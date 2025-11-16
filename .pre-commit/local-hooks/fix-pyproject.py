#!/usr/bin/env python3
"""Local pre-commit hook to fix pyproject.toml."""
import re
from pathlib import Path


def main():
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return 0

    content = pyproject.read_text(encoding="utf-8")
    if "readme-content-type" in content:
        content = re.sub(
            r"^readme-content-type\s*=.*\n?",
            "",
            content,
            flags=re.MULTILINE,
        )
        pyproject.write_text(content, encoding="utf-8")
        print("Removed readme-content-type from pyproject.toml")
        return 1  # File was modified
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
