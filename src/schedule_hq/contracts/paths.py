"""Portable paths and confined migration reads."""
from pathlib import Path,PurePosixPath
import re
def portable(path):
    if not isinstance(path,str) or not path or "\\" in path or ":" in path or path.startswith("/"): raise ValueError("unsafe path")
    parts=path.split("/")
    for part in parts:
        if part in ("",".","..") or part[-1] in " ." or not re.fullmatch(r"[A-Za-z0-9_.-]+",part) or part.split(".")[0].upper() in {"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}:
            raise ValueError("unsafe path segment")
    return PurePosixPath(path)
def confined(root,path):
    root=Path(root).resolve(strict=True)
    p=root
    for part in portable(path).parts:
        p=p/part
        if p.is_symlink(): raise ValueError("symlink forbidden")
    if not p.resolve().is_relative_to(root): raise ValueError("escaped root")
    return p
def unique_paths(paths):
    seen=set()
    for p in paths:
        key=str(portable(p)).casefold()
        if key in seen or any(key.startswith(x+"/") or x.startswith(key+"/") for x in seen): raise ValueError("path collision")
        seen.add(key)
