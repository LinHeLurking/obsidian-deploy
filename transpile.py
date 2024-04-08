import os
import re
import shutil
import sys
from dataclasses import dataclass
from os import path as osp
from typing import Dict

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
    WIKI_LINK_PATTERN = re.compile(r"(!)?\[\[(.+)(\|.+)?\]\]")
    IMAGE_EXT = (
        ".jpg",
        "jpeg",
        ".png",
        ".webp",
    )

    def __init__(self, vault_path: str, hugo_root_path: str):
        self.vault_path = vault_path
        self.hugo_root_path = hugo_root_path
        self.files: Dict[str, FileInfo] = {}
        self.name2path: Dict[str, str] = {}

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
        rewrite = []
        def repl(match_obj: re.Match):
            inline, target, display = match_obj.groups()
            if inline is None:
                inline = ""
            if display is None:
                display = ""
            assert target is not None
            guess_name = target
            if guess_name.endswith(".md"):
                guess_name = guess_name[:-3]
            guess_names = (f"{guess_name}.md", guess_name)
            for name in guess_names:
                if name in self.name2path:
                    abs_path = self.name2path[name]
                    if abs_path in self.files:
                        file_info = self.files[abs_path]
                        if "slug" in file_info.meta:
                            rel_path = osp.relpath(abs_path, self.vault_path)
                            if osp.sep == "\\":
                                rel_path = rel_path.replace("\\", "/")
                            rel_path.replace(name, file_info.meta["slug"])
                            target = rel_path
                        elif "url" in file_info.meta:
                            target = file_info.meta["url"]
                    break

            # TODO: url encode for target!

            link = f"{inline}[{target}]({display})"
            print(f"Rewrite wiki link as {link}")
            return link

        res = re.sub(self.WIKI_LINK_PATTERN, repl, file_content)
        return res

    def accept_md(self, file_info: FileInfo) -> bool:
        return True

    def rewrite_md(self, file_info: FileInfo) -> FileInfo:
        rewriters = (
            self.rewrite_rule_latex,
            self.rewrite_rule_delete_line,
        )
        for rewriter in rewriters:
            file_info.content = rewriter(file_info.content)
        return file_info

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
            file_info = FileInfo(file_path, file_meta, file_content)
            if self.accept_md(file_info):
                self.files[file_path] = self.rewrite_md(file_info)

    def copy_images(self):
        image_src_path = osp.join(self.vault_path, "images")
        image_dst_path = osp.join(self.hugo_root_path, "static")
        image_dst_path = osp.join(image_dst_path, "images")
        if osp.exists(image_dst_path):
            shutil.rmtree(image_dst_path)
        if osp.exists(image_src_path) and osp.isdir(image_src_path):
            shutil.copytree(image_src_path, image_dst_path)

    def write_md(self):
        pass

    def transpile(self):
        self.load_file()
        self.parse_md()
        self.write_md()
        self.copy_images()


def main():
    assert len(sys.argv) >= 3, "<transpile.py> vault_path hugo_root_path"
    vault_path = sys.argv[1]
    hugo_root_path = sys.argv[2]
    Transpiler(vault_path, hugo_root_path).transpile()


if __name__ == "__main__":
    main()
