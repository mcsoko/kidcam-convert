# kidcam-convert
Batch convert video files from kids camera to modern format

## Setup
` brew install ffmpeg `

## Instructions
` python3 kidcam_convert.py --input <dir> --output <dir> `

## macOS Shortcut Usage
You can also use the macOS Shortcut version as an alternative:

- To create the Shortcut, build it manually in the Shortcuts app and export it via **File → Export…**. The exported `.shortcut` file can be imported on other Macs using the `shortcuts import` command.
- Note that as of macOS Sequoia, `shortcuts export` was removed from the CLI.
- Run the Shortcut on a folder via Finder or via the terminal:
  `shortcuts run "Convert KidCam (HEVC)" --input-path <folder>`
- Ensure that ffmpeg is installed (`brew install ffmpeg`).
- This Shortcut is self-contained and does not require editing any `.py` paths.