import os, json, argparse, datetime, hashlib

DEFAULT_BINARY_EXT = {
    ".exe",".dll",".bin",".dat",".so",".dylib",
    ".png",".jpg",".jpeg",".gif",".bmp",".ico",".webp",
    ".pdf",".zip",".7z",".rar",".tar",".gz",".xz",
    ".mp3",".wav",".flac",".ogg",".mp4",".mkv",".mov",".avi",
    ".gguf",".onnx",".pt",".pth",".safetensors"
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",".hg",".svn","node_modules","__pycache__",
    ".venv","venv","dist","build",".mypy_cache",".pytest_cache",
    ".idea",".vscode",".DS_Store"
}

def is_binary_probe(path, probe=1024):
    try:
        with open(path, "rb") as f:
            chunk = f.read(probe)
        return b"\x00" in chunk
    except Exception:
        return True

def read_text_full(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        try:
            with open(path, "rb") as f:
                data = f.read()
            return data.decode("utf-8", errors="replace")
        except Exception:
            return None

def sha256_file(path, head_bytes=0):
    """Hash hele filen (head_bytes=0) eller kun første head_bytes (raskere)."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            if head_bytes and head_bytes > 0:
                h.update(f.read(head_bytes))
            else:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def depth_of(root, full):
    rel = os.path.relpath(full, root)
    if rel == os.path.basename(full):
        return 0
    return rel.count(os.sep)

def list_dirs_and_files(root, excludes):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in excludes]
        dirnames.sort(key=str.lower)
        filenames.sort(key=str.lower)
        yield dirpath, dirnames, filenames

def main():
    ap = argparse.ArgumentParser(description="Export directory tree to a single JSON file for AI review, with context.")
    ap.add_argument("root", help="Root directory to scan")
    ap.add_argument("outfile", help="Output JSON path")
    # Krav fra deg:
    ap.add_argument("--content-threshold-bytes", type=int, default=50*1024,
                    help="Include full content only for text files ≤ this size (default 50KB).")
    ap.add_argument("--hash-head-bytes", type=int, default=0,
                    help="If >0, hash only first N bytes instead of full file (faster). Default 0 = full file.")
    # Praktisk:
    ap.add_argument("--exclude-dirs", nargs="*", default=[],
                    help="Directory names to exclude in addition to defaults (e.g., node_modules .git .venv).")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    threshold = int(args.content_threshold_bytes)
    excludes = set(d.lower() for d in DEFAULT_EXCLUDE_DIRS)
    excludes.update(d.lower() for d in args.exclude_dirs)

    # Stats & kontekst
    files_total = 0
    dirs_total = 0
    empty_dirs = 0
    files_with_content = 0
    files_hashed = 0
    binaries = 0
    too_large_text = 0
    sum_size_all_files = 0

    # Toppnivå-oversikt (kun direkte barn av root)
    try:
        top_names = sorted(os.listdir(root), key=str.lower)
        top_level = {
            "directories": [n for n in top_names if os.path.isdir(os.path.join(root, n)) and n.lower() not in excludes],
            "files": [n for n in top_names if os.path.isfile(os.path.join(root, n))]
        }
    except Exception:
        top_level = {"directories": [], "files": []}

    # JSON-struktur (rekkefølge bevart)
    result = {
        "context": {
            "project_name": os.path.basename(root.rstrip("/\\")) or ".",
            "purpose": "Provide an AI-friendly, structured snapshot of this project: directories, files, and selective content.",
            "how_to_read": [
                "Process 'items' in order: directories first (alphabetical), then files (alphabetical) per directory.",
                "Use 'depth' to reconstruct hierarchy: root=0, first subdirectory=1, etc.",
                "For files: if 'content' exists it's a small text file ≤ threshold; otherwise rely on metadata and 'sha256'.",
                "Timestamps and sizes help reason about recency and heft; empty directories include a note."
            ],
            "depth_rules": "Depth equals the number of path separators from the root. Root directory has depth 0.",
            "content_policy": {
                "text_files_included_if_bytes_lte": threshold,
                "binary_or_over_threshold": "no content; SHA-256 recorded",
                "binary_detection": "file extension + null-byte probe"
            },
            "scan_config": {
                "root": root.replace("\\","/"),
                "exclude_dirs_effective": sorted(list(excludes)),
                "hash_head_bytes": args.hash_head_bytes
            },
            "overview": {
                "will_be_filled_after_scan": True
            },
            "top_level": top_level,
            "toc": []  # fylles fortløpende: kun path + type, i skannerekkefølge
        },
        "schema": {
            "item_object": {
                "type": "directory | file",
                "depth": "0 = root, 1 = subdir, ...",
                "path": "Relative path from root",
                "is_empty": "directories only",
                "note": "extra human-readable info for empty directories",
                "size_bytes": "files only",
                "ext": "file extension",
                "is_binary": "heuristic + extension",
                "skipped_reason": "why content was omitted (binary, over_threshold, read_error)",
                "content": "full text (only for small text files)",
                "sha256": "fingerprint for files with omitted content (or always for binaries)"
            }
        },
        "items": []
    }

    # Legg inn rotkatalogen
    result["context"]["toc"].append({"type":"directory","path":"."})
    result["items"].append({"type":"directory","depth":0,"path":".","is_empty":False})
    dirs_total += 1

    # Gå gjennom treet
    for dirpath, dirnames, filenames in list_dirs_and_files(root, excludes):
        if dirpath != root:
            rel_dir = os.path.relpath(dirpath, root).replace("\\","/")
            is_empty = (len(filenames) == 0 and len(dirnames) == 0)
            entry = {
                "type":"directory",
                "depth": depth_of(root, dirpath),
                "path": rel_dir,
                "is_empty": is_empty
            }
            if is_empty:
                entry["note"] = "No files in this directory."
                empty_dirs += 1
            result["context"]["toc"].append({"type":"directory","path":rel_dir})
            result["items"].append(entry)
            dirs_total += 1

        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root).replace("\\","/")
            size = os.path.getsize(fpath)
            ext  = os.path.splitext(fpath)[1].lower()
            depth = depth_of(root, fpath)

            sum_size_all_files += size
            files_total += 1

            is_binary = (ext in DEFAULT_BINARY_EXT) or is_binary_probe(fpath, 1024)

            item = {
                "type":"file",
                "depth": depth,
                "path": rel,
                "size_bytes": int(size),
                "ext": ext,
                "is_binary": bool(is_binary)
            }

            result["context"]["toc"].append({"type":"file","path":rel})

            if is_binary or size > threshold:
                item["skipped_reason"] = "binary" if is_binary else "over_threshold"
                item["sha256"] = sha256_file(fpath, head_bytes=args.hash_head_bytes)
                if is_binary:
                    binaries += 1
                    files_hashed += 1  # vi hasher binære også
                else:
                    too_large_text += 1
                    files_hashed += 1
                result["items"].append(item)
                continue

            # liten tekstfil – inkluder innhold
            text = read_text_full(fpath)
            if text is None:
                item["skipped_reason"] = "read_error"
                result["items"].append(item)
            else:
                item["content"] = text
                files_with_content += 1
                result["items"].append(item)

    # Edge case: helt tomt tre (kun root)
    if len(result["items"]) == 1:
        result["items"][0]["is_empty"] = True
        result["items"][0]["note"] = "No files in this directory."
        empty_dirs += 1

    # Fyll inn overview etter skann
    result["context"]["overview"] = {
        "directories_total": dirs_total,
        "empty_directories": empty_dirs,
        "files_total": files_total,
        "files_with_content": files_with_content,
        "files_hashed_or_metadata_only": files_hashed,
        "binary_files_detected": binaries,
        "too_large_text_files": too_large_text,
        "sum_size_all_files_bytes": int(sum_size_all_files)
    }

    # Skriv JSON
    with open(args.outfile, "w", encoding="utf-8", newline="\n") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)

    print(f"Done. Output: {args.outfile}")

if __name__ == "__main__":
    main()
