import re
import sys
from os import path as osp

from obsidian_to_hugo import ObsidianToHugo


def escape_latex_repl(match_obj: re.Match):
    return "{{< raw >}}" + match_obj.group(0) + "{{< /raw >}}"


def escape_latex(file_contents: str) -> str:
    pattern = r"\${1,2}[^\$]+\${1,2}"
    pattern = re.compile(pattern)
    res = re.sub(pattern, escape_latex_repl, file_contents)
    return res


def filter_file(file_contents: str, file_path: str) -> bool:
    # do something with the file path and contents
    # print(file_path)
    ignore = "hugo-hidden" in file_path or "Hugo Hidden" in file_path
    return not ignore


def transpile(vault_path: str, hugo_site_path: str):
    hugo_content_path = osp.join(hugo_site_path, "content")
    obsidian_to_hugo = ObsidianToHugo(
        obsidian_vault_dir=vault_path,
        hugo_content_dir=hugo_content_path,
        filters=[filter_file],
        processors=[escape_latex],
    )

    obsidian_to_hugo.run()


if __name__ == "__main__":
    assert len(sys.argv) >= 3, "<transpile.py> vault_path hugo_content_path"
    vault_path = sys.argv[1]
    hugo_site_path = sys.argv[2]
    transpile(vault_path, hugo_site_path)
