from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    """Copy the template pack and schemas into the wheel."""

    def run(self) -> None:
        super().run()
        root = Path(__file__).parent
        dest = Path(self.build_lib) / "guardrails" / "_assets"
        for name in ("pack", "schema"):
            source = root / name
            if source.exists():
                shutil.copytree(source, dest / name, dirs_exist_ok=True)


setup(cmdclass={"build_py": BuildPy})
