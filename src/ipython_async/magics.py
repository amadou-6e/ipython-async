import sys
import os
import queue
import subprocess
import threading
from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.display import display, update_display
from IPython import get_ipython
import ipywidgets as widgets


class CapturingOutput(widgets.Output):
    """
    A custom output widget that captures text in an internal buffer and updates
    its display with a MIME bundle.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.captured_text = ""

    def append_text(self, text):
        self.captured_text += text
        # Always update with a dict (MIME bundle) so that raw=True works.
        update_display({"text/plain": self.captured_text}, display_id=self.display_id, raw=True)


@magics_class
class AsyncMagics(Magics):
    """Magics for asynchronous execution of code in different environments."""

    @cell_magic
    def asynccmd(self, line, cell=None):
        """
        Execute a shell command asynchronously and stream its output.
        
        Usage:
          %%asynccmd [optional options]
          your command(s) here
        """
        return self._run_async_shell(line, cell, shell="cmd")

    @cell_magic
    def asyncbash(self, line, cell=None):
        """
        Execute bash commands asynchronously.
        
        Usage:
          %%asyncbash [optional options]
          your bash command(s) here
        """
        return self._run_async_shell(line, cell, shell="bash")

    @cell_magic
    def asyncpowershell(self, line, cell=None):
        """
        Execute PowerShell commands asynchronously.
        
        Usage:
          %%asyncpowershell [optional options]
          your PowerShell command(s) here
        """
        return self._run_async_shell(line, cell, shell="powershell")

    @cell_magic
    def asyncpython(self, line, cell=None):
        """
        Execute Python code asynchronously in a separate process.
        
        Usage:
          %%asyncpython [optional options]
          your Python code here
        """
        return self._run_async_python(line, cell)

    def _run_async_shell(self, line, cell, shell="cmd"):
        """Internal method to run shell commands asynchronously."""
        # Combine line and cell content to get the full command.
        command = line
        if cell:
            command = command + "\n" + cell if command else cell
        command = command.strip()

        if not command:
            print("No command provided.")
            return

        # Create a capturing output widget with improved styling.
        output_area = CapturingOutput(
            layout={
                'border': '1px solid #cccccc',
                'max_height': '300px',
                'overflow_y': 'auto',
                'padding': '8px',
                'margin': '5px 0',
                'font-family': 'monospace'
            })
        # Create a unique display_id for persistent output.
        display_id = "async_output_{}".format(id(output_area))
        output_area.display_id = display_id
        display(output_area, display_id=display_id)

        # Prepare the shell-specific command.
        if shell == "bash" and sys.platform != "linux":
            if sys.platform == "win32":
                exec_command = ["bash", "-c", command]
            else:  # macOS
                exec_command = ["/bin/bash", "-c", command]
        elif shell == "powershell" and sys.platform == "win32":
            # Append '; exit' to force termination.
            exec_command = ["powershell", "-NoProfile", "-Command", f"& {{ {command}; exit }}"]
        elif shell == "cmd":
            # Join lines to form one command string.
            exec_command = ["cmd", "/c", f"@echo off & {' '.join(command.splitlines())}"]

        def run_command():
            try:
                process = subprocess.Popen(
                    exec_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=isinstance(exec_command, str),
                    universal_newlines=True,
                    bufsize=1,
                )

                # Read and capture output until the process finishes.
                while True:
                    line_out = process.stdout.readline()
                    if line_out:
                        output_area.append_text(line_out)
                    else:
                        if process.poll() is not None:
                            break

                process.stdout.close()
                return_code = process.wait()
                if return_code == 0:
                    output_area.append_text("\n[Command completed successfully]")
                else:
                    output_area.append_text(f"\n[Command failed with exit code: {return_code}]")
            except Exception as e:
                output_area.append_text(f"\n[Error: {str(e)}]")

        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
        return thread

    def _run_async_python(self, line, cell):
        """Run Python code asynchronously in a new thread sharing the current context."""
        if not cell and not line:
            print("No Python code provided.")
            return

        # Combine code from the line and cell.
        code = line + "\n" + cell if line else cell

        # Create a capturing output widget.
        output_area = CapturingOutput(
            layout={
                'border': '1px solid #cccccc',
                'max_height': '300px',
                'overflow_y': 'auto',
                'padding': '8px',
                'margin': '5px 0',
                'font-family': 'monospace'
            })
        display_id = "async_output_{}".format(id(output_area))
        output_area.display_id = display_id
        display(output_area, display_id=display_id)

        def run_python_code():
            try:
                import sys
                import io
                import threading

                # Create pipe-like objects for output capture
                output_read, output_write = io.StringIO(), io.StringIO()

                # Flag to signal when execution is complete
                execution_completed = threading.Event()

                # Define a custom print function that writes to our pipe
                def custom_print(*args, **kwargs):
                    end = kwargs.get('end', '\n')
                    sep = kwargs.get('sep', ' ')
                    s = sep.join(str(arg) for arg in args) + end
                    output_write.write(s)

                ip = get_ipython()
                # Use the interactive namespace with our custom print
                namespace = ip.user_ns if ip is not None else globals()
                local_ns = dict(namespace)
                local_ns["print"] = custom_print

                # Thread to execute the user's code
                def execute_code():
                    try:
                        exec(code, local_ns)
                        execution_completed.set()
                    except Exception as e:
                        import traceback
                        error_msg = traceback.format_exc()
                        output_write.write(f"\n[Error: {error_msg}]")
                        execution_completed.set()

                # Start execution thread
                exec_thread = threading.Thread(target=execute_code, daemon=True)
                exec_thread.start()

                last_position = 0
                # While true loop for continuous output monitoring - this matches the subprocess pattern
                while True:
                    # Get current buffer content
                    content = output_write.getvalue()
                    new_content = content[last_position:]

                    # If there's new content, update the output area
                    if new_content:
                        output_area.append_text(new_content)
                        last_position = len(content)

                    # Check if execution is complete
                    if execution_completed.is_set() and not exec_thread.is_alive():
                        # One final check for any remaining output
                        content = output_write.getvalue()
                        if len(content) > last_position:
                            output_area.append_text(content[last_position:])

                        # Add completion message
                        output_area.append_text("\n[Python code executed successfully]")
                        break

                    # Small delay to prevent excessive CPU usage
                    import time
                    time.sleep(0.1)

            except Exception as e:
                output_area.append_text(f"\n[Error during execution setup: {str(e)}]")

        thread = threading.Thread(target=run_python_code, daemon=True)
        thread.start()
        return thread
