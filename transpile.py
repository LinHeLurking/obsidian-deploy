import re
import sys
import os
from os import path as osp
import shutil

from obsidian_to_hugo import ObsidianToHugo


def escape_latex_repl(match_obj: re.Match):
    return "{{< raw >}}" + match_obj.group(0) + "{{< /raw >}}"


def escape_latex(file_contents: str) -> str:
    pattern = r"\${1,2}[^\$]+\${1,2}"
    pattern = re.compile(pattern)
    res = re.sub(pattern, escape_latex_repl, file_contents)
    return res


def rewrite_delete_line_repl(match_obj: re.Match):
    return f"<del>{match_obj.group(0)}</del>"


def rewrite_delete_line(file_contents: str) -> str:
    pattern = r"~~[^~]+~~"
    pattern = re.compile(pattern)
    res = re.sub(pattern, rewrite_delete_line_repl, file_contents)
    return res


def filter_file(file_contents: str, file_path: str) -> bool:
    # do something with the file path and contents
    # print(file_path)
    ignore = "hugo-hidden" in file_path or "Hugo Hidden" in file_path
    ext = file_path.split(".")[-1]
    ignore_ext = ("jpg", "png", "jpeg", "webp")
    ignore = ignore or ext in ignore_ext
    return not ignore


def transpile(vault_path: str, hugo_root_path: str):
    hugo_content_path = osp.join(hugo_root_path, "content")
    if not osp.exists(hugo_content_path):
        os.makedirs(hugo_content_path)
    obsidian_to_hugo = ObsidianToHugo(
        obsidian_vault_dir=vault_path,
        hugo_content_dir=hugo_content_path,
        filters=[filter_file],
        processors=[escape_latex, rewrite_delete_line],
    )

    obsidian_to_hugo.run()

    # copy images into static directory
    image_src_path = osp.join(vault_path, "images")
    image_dst_path = osp.join(hugo_root_path, "static")
    image_dst_path = osp.join(image_dst_path, "images")
    if osp.exists(image_dst_path):
        shutil.rmtree(image_dst_path)
    if osp.exists(image_src_path) and osp.isdir(image_src_path):
        shutil.copytree(image_src_path, image_dst_path)


if __name__ == "__main__":
    assert len(sys.argv) >= 3, "<transpile.py> vault_path hugo_root_path"
    vault_path = sys.argv[1]
    hugo_root_path = sys.argv[2]
    transpile(vault_path, hugo_root_path)
