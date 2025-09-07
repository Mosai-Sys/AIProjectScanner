# AIProjectScanner
A simple tool (PowerShell and Python versions) that scans a directory (and all its subdirectories) and exports the full structure into a single structured JSON file. The goal is to provide AI-friendly project representations, including metadata about large or binary files, without dumping huge amounts of raw data.

# ProjectTreeToJson

A utility to **scan a project directory** (including subdirectories) and export the entire structure into a single **AI-friendly JSON file**.
This version adds a **context block** at the top of the JSON so that a language model can immediately understand how to interpret the data and how the project structure fits together.

## Features

* **Recursive scan** of a root directory and all subdirectories.
* **Directories**: included even if empty.

  * Empty directories carry both `is_empty: true` and a `note: "No files in this directory."`
* **Files**: included with metadata (`path`, `depth`, `size_bytes`, `ext`, `is_binary`).
* **Content policy**:

  * Small text files (≤ **50 KB**) → full content included.
  * Large files (> 50 KB) → no content, only metadata + SHA-256 hash.
  * Binary files (detected by extension or null-byte probe) → no content, SHA-256 hash included.
* **Context block** at the top of JSON includes:

  * `purpose`, `how_to_read`, `depth_rules`
  * `content_policy` (explaining size threshold and hash behavior)
  * `scan_config` (root, excludes, hash settings)
  * `overview` (counts of files, dirs, sizes, how many got content vs hash only)
  * `top_level` (immediate children of the root)
  * `toc` (table of contents: type+path for every item in scan order)
* Output is deterministic: directories and files are sorted alphabetically.
* Hashing can be configured to cover the entire file or just the first N bytes for speed.

## Usage

### Requirements

* Python 3.8 or newer

### Run

```bash
python export_tree_to_json.py <root_directory> <output_file.json>
```

#### Example

```bash
python export_tree_to_json.py "C:\Projects\MyApp" "C:\Projects\MyApp\tree.json" ^
  --exclude-dirs node_modules .git .venv venv __pycache__ dist build .vscode .idea
```


## Options

| Option                      | Default         | Description                                                                          |
| --------------------------- | --------------- | ------------------------------------------------------------------------------------ |
| `--content-threshold-bytes` | `51200` (50 KB) | Max file size for including full text content. Larger files will be hashed only.     |
| `--hash-head-bytes`         | `0`             | If > 0, only hash the first N bytes instead of the full file (faster).               |
| `--exclude-dirs`            | See defaults    | Additional directories to exclude (on top of `.git`, `node_modules`, `.venv`, etc.). |


## Example Output (simplified)

```json
{
  "context": {
    "project_name": "MyApp",
    "purpose": "Provide an AI-friendly, structured snapshot of this project: directories, files, and selective content.",
    "how_to_read": [
      "Process 'items' in order: directories first (alphabetical), then files (alphabetical) per directory.",
      "Use 'depth' to reconstruct hierarchy: root=0, first subdirectory=1, etc.",
      "For files: if 'content' exists it's a small text file ≤ threshold; otherwise rely on metadata and 'sha256'.",
      "Empty directories include a note."
    ],
    "content_policy": {
      "text_files_included_if_bytes_lte": 51200,
      "binary_or_over_threshold": "no content; SHA-256 recorded"
    },
    "overview": {
      "directories_total": 14,
      "empty_directories": 3,
      "files_total": 92,
      "files_with_content": 74,
      "files_hashed_or_metadata_only": 18,
      "binary_files_detected": 5,
      "too_large_text_files": 13,
      "sum_size_all_files_bytes": 45673212
    },
    "top_level": {
      "directories": ["src", "tests", "docs"],
      "files": ["README.md", "requirements.txt"]
    },
    "toc": [
      {"type": "directory", "path": "."},
      {"type": "file", "path": "README.md"},
      {"type": "directory", "path": "src"},
      {"type": "file", "path": "src/main.py"}
    ]
  },
  "items": [
    {
      "type": "directory",
      "depth": 0,
      "path": ".",
      "is_empty": false
    },
    {
      "type": "file",
      "depth": 0,
      "path": "README.md",
      "size_bytes": 1523,
      "ext": ".md",
      "is_binary": false,
      "content": "# MyApp\n\nThis is the readme..."
    },
    {
      "type": "file",
      "depth": 1,
      "path": "models/llama-7b.gguf",
      "size_bytes": 4210323456,
      "ext": ".gguf",
      "is_binary": true,
      "skipped_reason": "binary",
      "sha256": "c7f4...9a1"
    },
    {
      "type": "directory",
      "depth": 2,
      "path": "src/utils/empty_dir",
      "is_empty": true,
      "note": "No files in this directory."
    }
  ]
}
```

## Typical Use Cases

* **AI-assisted project analysis**: Feed the JSON into an LLM for structured code review or architecture mapping.
* **Project onboarding**: New developers can see the structure and know which files are important.
* **Documentation & archiving**: Snapshot of project hierarchy with selective content.
* **Model inventorying**: Large or binary assets (.gguf, .onnx, .pt) are captured with SHA-256 for reproducibility.

## Performance Tips

* **Use `--exclude-dirs`** to skip heavy folders (`node_modules`, `.git`, build artifacts, caches). This drastically reduces runtime and JSON size.
* **Adjust `--hash-head-bytes`**:

  * `0` (default) → full-file hash (slower, but precise).
  * `262144` (256 KB) → hash only the first 256 KB of each large file (faster, good enough to uniquely identify most assets).
* **Lower content threshold** if you have many medium-sized text files. Example:

  ```bash
  --content-threshold-bytes 20480
  ```

  (Only include full content if ≤ 20 KB.)
* **Run on SSD/NVMe**: hashing large binaries can otherwise bottleneck on disk speed.
* **Parallelize** if scanning extremely large repos: you can split scans per subdirectory and merge JSON later.

## Contributing

Contributions are welcome! Here’s how you can help:

1. **Fork the repository** and create a feature branch (`git checkout -b feature/my-improvement`).
2. **Follow code style**: keep functions small, add docstrings, and prefer explicit variable names.
3. **Test your changes** on both Windows and Linux/macOS if possible.
4. **Open a Pull Request** with a clear description of:

   * The problem you’re solving
   * The solution you implemented
   * Any limitations or trade-offs
5. **Be respectful** in code reviews. This project values clarity, maintainability, and reproducibility.

For bug reports, please open an **Issue** and include:

* OS and Python version
* Command you ran
* Expected vs actual result
* Example snippet of problematic JSON (if possible)

## License

MIT License – free to use, modify, and distribute.

