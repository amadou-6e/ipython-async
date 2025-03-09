import sys
import os
import tempfile
import io
import contextlib
import threading
import pytest
import time
from .conftest import *

import ipywidgets as widgets
import magics
from magics import AsyncMagics, display


# ---------------------------------------------------------
# Dummy CapturingOutput to replace CapturingOutput in our module
# ---------------------------------------------------------
class DummyCapturingOutput:
    """
    A dummy replacement for CapturingOutput that simply accumulates text.
    """

    def __init__(self, layout=None):
        self.layout = layout
        self.captured_text = ""
        self.display_id = None

    def append_text(self, text):
        self.captured_text += text


# ---------------------------------------------------------
# Dummy display and update_display to capture widget output
# ---------------------------------------------------------
captured_output_widgets = []


def dummy_display(widget, **kwargs):
    # Record display_id if provided.
    widget.display_id = kwargs.get("display_id", None)
    captured_output_widgets.append(widget)


def dummy_update_display(data, display_id, **kwargs):
    # In our dummy version, do nothing.
    pass


# ---------------------------------------------------------
# Fixture: Patch CapturingOutput, display, and update_display in our module
# ---------------------------------------------------------
@pytest.fixture(autouse=True)
def patch_widgets_display(monkeypatch):
    import magics
    # Patch the CapturingOutput class in our magics module.
    monkeypatch.setattr(magics,
                        "CapturingOutput",
                        lambda layout=None: DummyCapturingOutput(layout=layout))
    monkeypatch.setattr(magics, "display", dummy_display)
    monkeypatch.setattr(magics, "update_display", dummy_update_display)
    captured_output_widgets.clear()


# ---------------------------------------------------------
# Helper: Wait for a thread to complete
# ---------------------------------------------------------
def wait_for_thread(thread, timeout=5):
    thread.join(timeout)
    assert not thread.is_alive(), "Thread did not finish in time"


# ---------------------------------------------------------
# Tests for the async magics
# ---------------------------------------------------------


def test_asynccmd_no_command(capsys):
    """
    When no command is provided, the magic should immediately print an error
    message and return None.
    """
    mag = AsyncMagics(shell=None)
    result = mag.asynccmd("", None)
    captured = capsys.readouterr().out
    assert "No command provided." in captured
    assert result is None


def test_asynccmd_with_loops():
    """
    Test the async shell magic using a command with for loops.
    Check that the persistent output widget gets a non-None display_id and that
    the expected output is printed.
    """
    mag = AsyncMagics(shell=None)
    # Windows cmd syntax for a loop (using & to separate commands)
    loop_command = (r'echo Starting loop... & '
                    r'for /L %i in (1,1,3) do ( echo Iteration %i & ping 127.0.0.1 -n 2 >nul ) & '
                    r'echo Loop complete')
    thread = mag.asynccmd(loop_command, None)
    # Wait for thread completion using a polling loop.
    timeout = 5
    start_time = time.time()
    while thread.is_alive() and time.time() - start_time < timeout:
        time.sleep(0.1)
    assert not thread.is_alive(), "Command execution timed out"

    # Verify output and display_id
    assert len(captured_output_widgets) == 1
    widget = captured_output_widgets[0]
    output_text = widget.captured_text
    assert widget.display_id is not None
    assert "Starting loop..." in output_text
    assert "Iteration 1" in output_text
    assert "Iteration 2" in output_text
    assert "Iteration 3" in output_text
    assert "Loop complete" in output_text
    assert "[Command completed successfully]" in output_text


def test_asyncpowershell():
    """
    Test the PowerShell magic with a looped timeout command.
    Always assume a Windows platform.
    """
    mag = AsyncMagics(shell=None)

    # PowerShell command with a loop and delay
    command = ('echo "Starting PowerShell..."; '
               'for ($i=1; $i -le 3; $i++) { echo "Iteration $i"; Start-Sleep -Seconds 1 } ; '
               'echo "PowerShell loop complete"')

    thread = mag.asyncpowershell(command, None)

    # Wait for thread completion using a timeout loop
    timeout = 5
    start_time = time.time()
    while thread.is_alive() and time.time() - start_time < timeout:
        time.sleep(0.1)

    assert not thread.is_alive(), "PowerShell execution timed out"

    # Verify output and display_id
    assert len(captured_output_widgets) == 1
    widget = captured_output_widgets[0]
    output_text = widget.captured_text
    assert widget.display_id is not None
    assert "Starting PowerShell..." in output_text
    assert "Iteration 1" in output_text
    assert "Iteration 2" in output_text
    assert "Iteration 3" in output_text
    assert "PowerShell loop complete" in output_text
    assert "[Command completed successfully]" in output_text


def test_asynccmd_failure():
    """
    Test a failing shell command.
    On Unix we list a non-existent directory.
    On Windows we use a command that immediately exits with an error.
    """
    mag = AsyncMagics(shell=None)
    if sys.platform == "win32":
        thread = mag.asynccmd("exit 1", None)
    else:
        thread = mag.asynccmd("ls /non_existent_directory", None)
    wait_for_thread(thread)
    assert len(captured_output_widgets) == 1
    widget = captured_output_widgets[0]
    output_text = widget.captured_text
    assert "Command failed with exit code:" in output_text


def test_asyncpython_success(monkeypatch):
    """
    Test the asyncpython magic with a looped timeout command.
    Always assume the correct platform.
    """
    temp_files = []
    original_NamedTemporaryFile = tempfile.NamedTemporaryFile

    def fake_NamedTemporaryFile(*args, **kwargs):
        f = original_NamedTemporaryFile(*args, **kwargs)
        temp_files.append(f.name)
        return f

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", fake_NamedTemporaryFile)
    mag = AsyncMagics(shell=None)

    # Python script with a loop and delay
    code = """import time
for i in range(1, 4):
    print(f"Iteration {i}", flush=True)
    time.sleep(1)
print("Python loop complete", flush=True)
"""

    thread = mag.asyncpython("", code)

    # Wait for thread completion using a timeout loop
    timeout = 5
    start_time = time.time()
    while thread.is_alive() and time.time() - start_time < timeout:
        time.sleep(0.1)

    assert not thread.is_alive(), "Python execution timed out"

    # Verify output and display_id
    assert len(captured_output_widgets) == 1
    widget = captured_output_widgets[0]
    output_text = widget.captured_text
    assert widget.display_id is not None
    assert "Iteration 1" in output_text
    assert "Iteration 2" in output_text
    assert "Iteration 3" in output_text
    assert "Python loop complete" in output_text
    assert "[Python code executed successfully]" in output_text

    # Ensure the temp file is deleted
    for filename in temp_files:
        assert not os.path.exists(filename), f"Temporary file {filename} was not deleted"


def test_asyncpython_failure():
    """
    Test the asyncpython magic with code that exits with an error.
    We add a print to ensure output is flushed so that the reading loop can complete.
    """
    mag = AsyncMagics(shell=None)
    code = ("print('error', flush=True)\n"
            "import sys\n"
            "sys.stdout.close()\n"
            "sys.exit(1)")
    thread = mag.asyncpython("", code)
    wait_for_thread(thread, timeout=10)
    assert len(captured_output_widgets) == 1
    widget = captured_output_widgets[0]
    output_text = widget.captured_text
    assert widget.display_id is not None
    assert "error" in output_text
    assert "Python execution failed with exit code:" in output_text


def test_parallel_cell_execution():
    """
    Simulate parallel cell execution by launching several asynchronous commands concurrently.
    Verify that each cell (widget) receives its own unique display_id and correct output.
    """
    mag = AsyncMagics(shell=None)
    threads = []

    # CMD loop: Print three iterations with a delay
    cmd_command = (r'echo Starting loop... & '
                   r'for /L %i in (1,1,3) do ( echo Iteration %i & ping 127.0.0.1 -n 2 >nul ) & '
                   r'echo Loop complete')
    threads.append(mag.asynccmd(cmd_command, None))

    # Python loop: Print three iterations with a delay
    python_code = """import time
for i in range(1, 4):
    print(f"Iteration {i}", flush=True)
    time.sleep(1)
print("Python loop complete", flush=True)
"""
    threads.append(mag.asyncpython("", python_code))

    # PowerShell loop (Windows only)
    if sys.platform == "win32":
        ps_command = (
            'echo "Starting PowerShell..."; '
            'for ($i=1; $i -le 3; $i++) { echo "Iteration $i"; Start-Sleep -Seconds 1 } ; '
            'echo "PowerShell loop complete"')
        threads.append(mag.asyncpowershell(ps_command, None))

    # Wait for all threads to finish
    for t in threads:
        wait_for_thread(t, timeout=10)

    # There should be at least two (or three on Windows) distinct widgets.
    num_expected = 3 if sys.platform == "win32" else 2
    assert len(captured_output_widgets) >= num_expected

    # Check that each widget has a unique display_id and expected output.
    display_ids = set()
    outputs = []
    for widget in captured_output_widgets:
        assert widget.display_id is not None
        display_ids.add(widget.display_id)
        outputs.append(widget.captured_text)
    assert len(display_ids) == num_expected

    # Validate expected outputs in each widget.
    # (Adjust the expected text if needed according to your command output.)
    assert any("Starting loop..." in out and "Iteration 1" in out and "Loop complete" in out
               for out in outputs)
    assert any("Iteration 1" in out and "Python loop complete" in out for out in outputs)
    if sys.platform == "win32":
        assert any("Starting PowerShell..." in out and "Iteration 1" in out and
                   "PowerShell loop complete" in out for out in outputs)


if __name__ == "__main__":
    pytest.main([__file__])
