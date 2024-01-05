import hashlib
import json
import operator
import os
import sys
from functools import reduce
from os import path as osp
from typing import Callable, Iterable

CHUNK_SIZE = 512
END_POINT = os.getenv("END_POINT")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

if not (END_POINT and ACCESS_KEY and SECRET_KEY):
    print("Provide `END_POINT`, `ACCESS_KEY` and `SECRET_KEY` in environment variable.")
    sys.exit(0)


def f_hash(path: str):
    hs = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            hs.update(chunk)
    hs = hs.hexdigest()
    return hs


def ignore_dot_file(d_root: str, name: str) -> bool:
    return name.startswith(".")


def ignore_s_in_dir(s: str):
    def wrapper(d_root: str, name: str) -> bool:
        return d_root.endswith(s) or f"{s}{osp.sep}" in d_root

    return wrapper


ignore_git_dir = ignore_s_in_dir(".git")
ignore_github_dir = ignore_s_in_dir(".github")


def scan_dir(
    cur_root: str,
    f_filter: Iterable[Callable[[str, str], bool]] = (
        ignore_dot_file,
        ignore_git_dir,
        ignore_github_dir,
    ),
):
    res = {}

    for d_root, d_names, f_names in os.walk(cur_root):
        for f_name in f_names:
            ignore = reduce(operator.or_, map(lambda op: op(d_root, f_name), f_filter))
            if ignore:
                continue
            f_path = osp.join(d_root, f_name)
            res[osp.relpath(f_path, hugo_site)] = f_hash(f_path)

    return res


def write_meta(d_path: str, meta: dict):
    with open(osp.join(d_path, ".meta.json"), "w") as f:
        json.dump(meta, f)


def read_meta(d_path: str) -> Optional[dict]:
    # TODO: replace with a remote meta
    f_path = osp.join(d_path, ".meta.json")
    if not osp.exists(f_path):
        return None
    with open(f_path, "w") as f:
        return json.load(f)


# TODO
def s3_del(l_path, r_path):
    pass


# TODO
def s3_upload(l_path, r_path):
    pass


def replace_on_change(cur_root, old_meta, meta):
    if old_meta is None:
        for k in meta:
            s3_upload(k, "")
        return
    for k in meta:
        if k not in old_meta:
            s3_del(k, "")
        elif meta[k] != old_meta[k]:
            s3_upload(k, "")


if __name__ == "__main__":
    cwd = os.getcwd()
    hugo_site = osp.join(cwd, "hugo-site")
    if not osp.exists(hugo_site):
        print(f"Cannot find `hugo-site` dir in {cwd}")
        sys.exit(0)
    old_meta = read_meta(hugo_site)
    meta = scan_dir(hugo_site)
    write_meta(hugo_site, meta)
