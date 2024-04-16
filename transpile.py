import os
import re
import shutil
import sys
from dataclasses import dataclass
from os import path as osp
from typing import Dict
from urllib.parse import quote

import yaml


@dataclass
class FileInfo:
    original_path: str
    meta: dict
    content: str

    def __post_init__(self):
        self.original_path = osp.abspath(self.original_path)


class Transpiler:
    LATEX_PATTERN = re.compile(r"\${1,2}[^\$]+\${1,2}")
    DELETE_LINE_PATTERN = re.compile(r"~~[^~]+~~")
    MD_LINK_PATTERN = re.compile(r"(!)?(\[.*\])(\(.*\))")
    WIKI_LINK_PATTERN = re.compile(r"\[\[([^\[\]\|]+)(\|.+)?\]\]")
    TRIM_LINK_PREFIX = os.getenv("TRIM_LINK_PREFIX", "blog/images/")
    MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\[\]]*)\]\((.+)\)")
    IMAGE_EXT = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    )

    def __init__(self, vault_path: str, hugo_root_path: str, dry_run: bool = False):
        self.vault_path = vault_path
        self.hugo_root_path = hugo_root_path
        self.files: Dict[str, FileInfo] = {}
        self.name2path: Dict[str, str] = {}
        self.dry_run = dry_run

    @classmethod
    def parse_meta(cls, content: str) -> dict:
        if content[:3] != "---":
            return {}
        idx = content.find("---", 3)
        assert idx >= 3
        meta = yaml.safe_load(content[3:idx])
        return meta

    @classmethod
    def rewrite_rule_latex(cls, file_content: str) -> str:
        def repl(match_obj: re.Match):
            return "{{< raw >}}" + match_obj.group(0) + "{{< /raw >}}"

        res = re.sub(cls.LATEX_PATTERN, repl, file_content)
        return res

    @classmethod
    def rewrite_rule_delete_line(cls, file_content: str) -> str:
        def repl(match_obj: re.Match):
            return f"<del>{match_obj.group(0)}</del>"

        res = re.sub(cls.DELETE_LINE_PATTERN, repl, file_content)
        return res

    def rewrite_rule_wiki_link(self, file_content: str) -> str:
        def repl(match_obj: re.Match):
            print(f"Rewriting wiki link: {match_obj.group(0)}")
            target, display = match_obj.groups()
            if display is None:
                display = target
            elif display.startswith(""):
                display = display[1:]

            assert target is not None
            if target.endswith(".md"):
                target = target[:-3]
            if target not in self.name2path:
                target += ".md"
            if target not in self.name2path:
                raise IOError(f"File {target} not found in directory")
            abs_path = self.name2path[target]
            if abs_path in self.files:
                file_info = self.files[abs_path]
                if "slug" in file_info.meta:
                    print("Replace file name with slug")
                    base_name = osp.basename(abs_path)
                    rel_path = osp.relpath(abs_path, self.vault_path)
                    if osp.sep == "\\":
                        rel_path = rel_path.replace("\\", "/")
                    target = rel_path.replace(base_name, file_info.meta["slug"])
                elif "url" in file_info.meta:
                    print("Replace file name with url")
                    target = file_info.meta["url"]
                if not target.startswith("/"):
                    target = "/" + target
            # Image in wiki link is in "[[xxx.png]]" format.
            # It has no path information in it
            ext = ""
            idx = target.rfind(".")
            if idx != -1:
                ext = target[idx:]
            if ext in self.IMAGE_EXT and "/" not in target:
                target = "/images/" + target

            # url encode
            target = quote(target)

            link = f"[{display}]({target})"
            print(f"Rewrite wiki link as {link}")
            return link

        res = re.sub(self.WIKI_LINK_PATTERN, repl, file_content)
        return res

    def rewrite_rule_plain_md_link(self, file_content: str):
        def repl(match_obj: re.Match):
            old_link = match_obj.group(0)
            display, target = match_obj.groups()
            if target.startswith(self.TRIM_LINK_PREFIX):
                target = target[len(self.TRIM_LINK_PREFIX) :]
            ext = ""
            idx = target.rfind(".")
            ext = target[idx:]
            if ext in self.IMAGE_EXT and "/" not in target:
                if not target.startswith("/"):
                    target = "/" + target
                target = "/images" + target

            # url encode

            link = f"[{display}]({target})"
            if link != old_link:
                print(f"Rewrite markdown link as {link}")
            return link

        res = re.sub(self.MARKDOWN_LINK_PATTERN, repl, file_content)
        return res

    def accept_md(self, file_info: FileInfo) -> bool:
        return True

    def rewrite_md(self) -> FileInfo:
        rewriters = (
            self.rewrite_rule_latex,
            self.rewrite_rule_delete_line,
            self.rewrite_rule_wiki_link,
            self.rewrite_rule_plain_md_link,
        )
        for k, v in self.files.items():
            file_info = v
            for rewriter in rewriters:
                file_info.content = rewriter(file_info.content)
            self.files[k] = file_info

    def load_file(self):
        for dir_path, _, file_names in os.walk(self.vault_path):
            if dir_path.startswith("."):
                continue
            for file_name in file_names:
                self.name2path[file_name] = osp.join(dir_path, file_name)

    def parse_md(self):
        for file_name, file_path in self.name2path.items():
            if not file_name.endswith(".md"):
                continue
            with open(file_path, "r") as f:
                file_content = f.read()
            file_meta = self.parse_meta(file_content)
            # if len(file_meta) > 0:
            #     print(f"Loaded metadata from {file_path} ({len(file_meta)} kv pais(s))")
            file_info = FileInfo(file_path, file_meta, file_content)
            if self.accept_md(file_info):
                self.files[file_path] = file_info

    def copy_images(self):
        if self.dry_run:
            return
        image_src_path = osp.join(self.vault_path, "images")
        image_dst_path = osp.join(self.hugo_root_path, "static")
        image_dst_path = osp.join(image_dst_path, "images")
        if osp.exists(image_dst_path):
            shutil.rmtree(image_dst_path)
        if osp.exists(image_src_path) and osp.isdir(image_src_path):
            shutil.copytree(image_src_path, image_dst_path)

    def write_md(self):
        if self.dry_run:
            return
        hugo_content_path = osp.join(self.hugo_root_path, "content")
        print(f"Removing old files in {hugo_content_path}")
        shutil.rmtree(hugo_content_path)
        if not osp.exists(hugo_content_path):
            os.makedirs(hugo_content_path)
        for file_info in self.files.values():
            path = file_info.original_path
            path = osp.relpath(path, self.vault_path)
            path = osp.join(hugo_content_path, path)
            if not osp.exists(osp.dirname(path)):
                os.makedirs(osp.dirname(path))
            with open(path, "w") as f:
                f.write(file_info.content)

    def transpile(self):
        self.load_file()
        self.parse_md()
        self.rewrite_md()
        self.write_md()
        self.copy_images()


def main():
    assert len(sys.argv) >= 3, "<transpile.py> vault_path hugo_root_path [dry_run]"
    vault_path = sys.argv[1]
    hugo_root_path = sys.argv[2]
    dry_run = False
    if len(sys.argv) >= 4 and sys.argv[3]:
        dry_run = True
    Transpiler(vault_path, hugo_root_path, dry_run).transpile()


if __name__ == "__main__":
    main()
