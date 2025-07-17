# VLC XSPF Cutter

This tool helps automate the process of cutting video clips using VLC bookmarks and `ffmpeg`.

## Features

- Uses `.xspf` playlist/bookmark files from VLC.
- Extracts and processes timestamps in pairs.
- First cut is made **5 seconds before** the first bookmark (if possible).
- Ensures correct `ffmpeg` re-encoding in second step.
- Handles edge case where bookmark is within first 5 seconds.

## Requirements

- Python 3.7+
- `ffmpeg` installed and in system path

## Usage

### Step 1: Prepare cuts

```bash
python prepareCuts.py -i "path/to/bookmarks.xspf" -t "output/dir"
```

This will create a `cuts.txt` file with all `ffmpeg` commands.

### Step 2: Execute cuts

```bash
python executeCuts.py
```

Executes all commands from `cuts.txt` sequentially.

## Output

- `clip001.mp4`, `clip002.mp4`, ... in the target folder.

## License

MIT © DEng.Lizard
