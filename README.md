# IPython Async

Run cells asynchronously in IPython/Jupyter across multiple shells (cmd, bash, python, powershell).

## Installation

```bash
pip install ipython-async
```

## Usage

Load the extension in your Jupyter notebook or IPython session:

```python
%load_ext ipython_async
```

### Available Cell Magics

#### `%%asynccmd`
Execute shell commands asynchronously using the system's default shell.

```
%%asynccmd
echo "This command runs in the background"
sleep 5
echo "Command finished"
```

#### `%%asyncbash`
Execute Bash commands asynchronously (works on Windows, Mac, and Linux).

```
%%asyncbash
for i in {1..5}; do
    echo "Processing item $i"
    sleep 1
done
echo "All items processed"
```

#### `%%asyncpowershell`
Execute PowerShell commands asynchronously (Windows only).

```
%%asyncpowershell
1..5 | ForEach-Object {
    Write-Output "Processing item $_"
    Start-Sleep -Seconds 1
}
Write-Output "All items processed"
```

#### `%%asyncpython`
Execute Python code asynchronously in a separate process.

```
%%asyncpython
import time

for i in range(5):
    print(f"Processing item {i+1}")
    time.sleep(1)
    
print("All items processed")
```

## Features

- Non-blocking execution - continue working in your notebook while commands run
- Live output streaming
- Cross-platform compatibility
- Support for multiple shell environments
- Simple, intuitive interface

## Requirements

- Python 3.6+
- IPython 7.0+
- ipywidgets 7.0+

## License

MIT License