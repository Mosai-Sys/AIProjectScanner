import os, json, argparse, datetime

DEFAULT_BINARY_EXT = {
    ".exe",".dll",".bin",".dat",".so",".dylib",
    ".png",".jpg",".jpeg",".gif",".bmp",".ico",".webp",
    ".pdf",".zip",".7z",".rar",".tar",".gz",".xz",
    ".mp3",".wav",".flac",".ogg",".mp4",".mkv",".mov",".avi",
    ".gguf",".onnx",".pt",".pth",".safetensors"
}

def is_binary_probe(path, probe=1024):
    try:
        with open(path, "rb") as f:
            chunk = f.read(probe)
        return b"\x00" in chunk
    except Exception:
        return True

def read_text_safe(path):
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

def depth_of(root, full):
    rel = os.path.relpath(full, root)
    if rel == os.path.basename(full):
        return 0
    return rel.count(os.sep)

def list_files_sorted(folder):
    try:
        names = os.listdir(folder)
    except PermissionError:
        return []
    files = [n for n in names if os.path.isfile(os.path.join(folder, n))]
    return [os.path.join(folder, n) for n in sorted(files, key=str.lower)]

def main():
    ap = argparse.ArgumentParser(description="Eksporter mappetre til én .json for AI-gjennomgang.")
    ap.add_argument("root", help="Rotmappe")
    ap.add_argument("outfile", help="Sti til output .json")
    ap.add_argument("--max-mb", type=int, default=3, help="Maks filstørrelse for innholdsinnlesing (MB). Store filer får KUN metadata.")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    max_bytes = args.max_mb * 1024 * 1024

    result = {
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "root": root,
        "notes": [
            "Depth: rotmappe=0, første undernivå=1, osv.",
            "Rekkefølge: mapper alfabetisk, deretter filer alfabetisk per mappe.",
            f"Filer > {args.max_mb} MB: ingen innhold/preview – kun metadata (sti, endelse, dybde, størrelse).",
            "Tomme mapper og tomme filer inkluderes.",
            "Schema: se 'schema'."
        ],
        "schema": {
            "item_object": {
                "type": "directory | file",
                "depth": "0 = rot, 1 = undernivå, ...",
                "path": "Relativ sti fra root",
                "is_empty": "Kun for mapper",
                "size_bytes": "Kun for filer",
                "ext": "Filendelse",
                "is_binary": "Heuristikk + endelse",
                "skipped_reason": "Angis når innhold ikke tas med (f.eks. 'too_large' eller 'binary')",
                "content": "Kun små tekstfiler (<= terskel). Aldri for store filer."
            }
        },
        "items": []
    }

    # Rotmappe
    result["items"].append({"type":"directory","depth":0,"path":".","is_empty":False})

    # Samle alle mapper
    all_dirs = [root]
    for d, subdirs, _ in os.walk(root):
        for s in subdirs:
            all_dirs.append(os.path.join(d, s))
    all_dirs = sorted(set(all_dirs), key=lambda p: p.lower())

    for d in all_dirs:
        if d != root:
            rel_d = os.path.relpath(d, root)
            result["items"].append({
                "type":"directory","depth":depth_of(root, d),"path":rel_d.replace("\\","/"),"is_empty":False
            })

        files = list_files_sorted(d)
        if not files and d != root:
            # marker mappen som tom
            for i in range(len(result["items"]) - 1, -1, -1):
                it = result["items"][i]
                if it["type"] == "directory" and it["path"] == os.path.relpath(d, root).replace("\\","/"):
                    it["is_empty"] = True
                    break

        for fpath in files:
            rel = os.path.relpath(fpath, root).replace("\\","/")
            size = os.path.getsize(fpath)
            ext  = os.path.splitext(fpath)[1].lower()
            depth = depth_of(root, fpath)

            is_bin = (ext in DEFAULT_BINARY_EXT) or is_binary_probe(fpath, 1024)

            item = {
                "type": "file",
                "depth": depth,
                "path": rel,
                "size_bytes": int(size),
                "ext": ext,
                "is_binary": bool(is_bin)
            }

            if is_bin:
                item["skipped_reason"] = "binary"
                result["items"].append(item)
                continue

            if size > max_bytes:
                item["skipped_reason"] = "too_large"
                result["items"].append(item)
                continue

            # liten tekstfil – les hele
            txt = read_text_safe(fpath)
            if txt is None:
                item["skipped_reason"] = "read_error"
            else:
                item["content"] = txt
            result["items"].append(item)

    with open(args.outfile, "w", encoding="utf-8", newline="\n") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)

    print(f"Ferdig. Output: {args.outfile}")

if __name__ == "__main__":
    main()
