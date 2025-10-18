# KidCam Convert

A lightweight tool for batch-converting kid camera videos to Apple-compatible HEVC `.mp4` files.  
- Auto-detects Apple Silicon hardware acceleration (`hevc_videotoolbox`)  
- Preserves creation dates and keeps Photos/iCloud sorting intact  
- Skips already-converted files and retains metadata  
- Usable via macOS Shortcut or Python CLI

## Usage Options

> There are two ways to use KidCam Convert:  
> 1. The macOS Shortcut (simplest and includes the script)  
> 2. The Python CLI (for advanced or automated use)

**Requirements:**  
Both methods require [`ffmpeg`](https://ffmpeg.org/). Install it with Homebrew: `brew install ffmpeg`.

### Option 1: macOS Shortcut
You can download the `.shortcut.zip` file directly from the GitHub release assets. This Shortcut includes the embedded Python script, so there is no need to have the `.py` file locally.

After downloading, unzip the file and double-click the `.shortcut` file to add it to the macOS Shortcuts app. Make sure `ffmpeg` is installed on your system (`brew install ffmpeg`).

The Shortcut automatically supports Apple Silicon hardware acceleration when available. When run, it will prompt you to select input and output folders, then convert the videos accordingly.

### Option 2: Command Line Interface (CLI)
The CLI tool auto-detects Apple Silicon hardware acceleration (`hevc_videotoolbox`) when available and supports both single input folders and paired input/output positional arguments. The second positional argument is treated as the output folder if provided.

Supported options:
- `--recursive`: Recursively process subdirectories.
- `--hw`: Force hardware-accelerated encoding.
- `--sw`: Force software encoding.
- `--verbose`: Enable verbose logging for detailed output.

Examples:

Single folder conversion (auto output):
```
python kidcam_convert.py /path/to/input_folder
```

Input + output positional paths:
```
python kidcam_convert.py /path/to/input_folder /path/to/output_folder
```

Recursive mode:
```
python kidcam_convert.py /path/to/input_folder --recursive
```

Forcing hardware encoding:
```
python kidcam_convert.py /path/to/input_folder --hw
```

Forcing software encoding:
```
python kidcam_convert.py /path/to/input_folder --sw
```

Verbose logging:
```
python kidcam_convert.py /path/to/input_folder --verbose
```

Combined example for full SD card conversion:
```
python kidcam_convert.py /Volumes/KidCamSD /Users/username/Videos/KidCamConverted --recursive --hw --verbose
```