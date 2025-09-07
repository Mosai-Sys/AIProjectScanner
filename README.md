# AIProjectScanner
A simple tool (PowerShell and Python versions) that scans a directory (and all its subdirectories) and exports the full structure into a single structured JSON file. The goal is to provide AI-friendly project representations, including metadata about large or binary files, without dumping huge amounts of raw data.

# Export-Tree-ToJson

A simple tool (PowerShell and Python versions) that scans a directory (and all its subdirectories) and exports the full structure into a single structured **JSON file**.
The goal is to provide AI-friendly project representations, including metadata about large or binary files, without dumping huge amounts of raw data.

---

## Features

* Recursively scans a chosen root directory and all subdirectories.
* Includes **directories (even empty ones)** and **files (even empty ones)**.
* Maintains order: directories are listed alphabetically, then files alphabetically within each directory.
* Adds **depth** information (`0 = root`, `1 = first subdirectory`, etc.).
* Small text files (≤ 3 MB) → full content included.
* Large files (> 3 MB) and binary files → only metadata (`path`, `ext`, `size_bytes`, `skipped_reason`).
* Adds a **notes** section at the top of the JSON to explain how to interpret the structure.
* Provides an inline **schema** definition for clarity.

---

## Usage

### PowerShell (Windows)

Run:

```powershell
.\Export-Tree-ToJson.ps1 -RootPath "C:\Users\Mediapc\Projects\MyApp" -OutFile "C:\Users\Mediapc\Projects\MyApp\project.json" -MaxFileSizeMB 3
```

### Python (Windows/macOS/Linux)

Requires Python 3:

```bash
python export_tree_to_json.py "C:\Users\Mediapc\Projects\MyApp" "C:\Users\Mediapc\Projects\MyApp\project.json" --max-mb 3
```

---

## Example Output

```json
{
  "generated_at": "2025-09-07T11:45:32+02:00",
  "root": "C:/Users/Mediapc/Projects/MyApp",
  "notes": [
    "Depth: root=0, first subdirectory=1, etc.",
    "Order: directories alphabetically, then files alphabetically within each directory.",
    "Files > 3 MB: only metadata is included, no content.",
    "Empty directories and empty files are included."
  ],
  "schema": {
    "item_object": {
      "type": "directory | file",
      "depth": "0 = root, 1 = subdirectory, ...",
      "path": "Relative path from root",
      "is_empty": "Only for directories",
      "size_bytes": "Only for files",
      "ext": "File extension",
      "is_binary": "Heuristic + extension check",
      "skipped_reason": "Why content was skipped (e.g., 'too_large', 'binary')",
      "content": "Full file content for small text files only"
    }
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
      "size_bytes": 1234,
      "ext": ".md",
      "is_binary": false,
      "content": "# My Project\n\nDocumentation here..."
    },
    {
      "type": "file",
      "depth": 1,
      "path": "models/llama-7b.gguf",
      "size_bytes": 4210323456,
      "ext": ".gguf",
      "is_binary": true,
      "skipped_reason": "binary"
    }
  ]
}
```

---

## Why JSON Instead of Text?

* Easier for AI models to parse and process systematically.
* Metadata (size, type, depth) is explicit.
* Large files and binaries are described without bloating the output.
* Preserves context (e.g., AI can “see” that `models/llama-7b.gguf` exists, its size, and type, even though content isn’t dumped).

---

## Typical Use Cases

* **AI-assisted code review:** feed the JSON to a language model for structured project analysis.
* **Documentation & archiving:** produce an overview of all files and folders.
* **Project onboarding:** new developers can see the entire structure and metadata at a glance.
* **Model inventorying:** identify large/binary files like `.gguf`, `.onnx`, `.pt` and their sizes without loading them.

---

## Output Structure

* **Root-level fields**: `generated_at`, `root`, `notes`, `schema`, `items`.
* **items**: ordered list of directories and files.
* **Directory objects**: `{ "type": "directory", "depth": 1, "path": "src", "is_empty": false }`
* **File objects**:

  * Small text file: includes `content`.
  * Large/binary file: includes `skipped_reason` but no content.

---

## License

MIT License – free to use, modify, and distribute.


