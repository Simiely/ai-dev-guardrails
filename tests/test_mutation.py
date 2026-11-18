from pathlib import Path

from guardrails.mutation import run_mutation


def test_mutation_skips_when_not_configured(tmp_path):
    result = run_mutation(tmp_path, {"commands": {}}, ["src/a.py"])
    assert result["ran"] is False
    assert "not configured" in result["reason"]


def test_mutation_passes_changed_files_to_command(tmp_path):
    command = (
        "python -c \"import os,sys; "
        "sys.exit(0 if 'src/a.py' in os.environ.get('GUARDRAILS_CHANGED_FILES','') else 1)\""
    )
    result = run_mutation(
        tmp_path,
        {"commands": {"mutation": command}},
        ["src/a.py"],
    )
    assert result["ran"] is True
    assert result["exit_code"] == 0
    assert result["files"] == ["src/a.py"]
