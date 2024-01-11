import hashlib
import json
import operator
import os
import sys
from functools import reduce
from os import path as osp
from typing import Callable, Dict, Iterable
import argparse
import boto3
import botocore
from botocore.config import Config

CHUNK_SIZE = 512
END_POINT = os.getenv("END_POINT")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

if not (END_POINT and ACCESS_KEY and SECRET_KEY and BUCKET_NAME):
    print(
        "Provide `END_POINT`, `ACCESS_KEY`, `SECRET_KEY` and `BUCKET_NAME` in environment variable."
    )
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


def ignore_dot_file(rel_d_root: str, name: str) -> bool:
    return name.startswith(".")


def ignore_font_file(rel_d_root: str, name: str) -> bool:
    return name.endswith(".ttf") or name.endswith(".woff") or name.endswith(".woff2")


def ignore_s_in_dir(s: str):
    def wrapper(rel_d_root: str, name: str) -> bool:
        return rel_d_root.endswith(s) or rel_d_root.endswith(f"{s}{osp.sep}")

    return wrapper


ignore_git_dir = ignore_s_in_dir(".git")
ignore_github_dir = ignore_s_in_dir(".github")


def get_local_meta(
    hugo_site_root: str,
    f_filter: Iterable[Callable[[str, str], bool]] = (
        ignore_dot_file,
        ignore_font_file,
        ignore_git_dir,
        ignore_github_dir,
    ),
) -> Dict[str, str]:
    res = {}
    hugo_site_public = osp.join(hugo_site_root, "public")
    for d_root, d_names, f_names in os.walk(hugo_site_public):
        rel_d_root = osp.relpath(d_root, hugo_site_public)
        for f_name in f_names:
            ignore = reduce(operator.or_, map(lambda op: op(rel_d_root, f_name), f_filter))
            if ignore:
                continue
            f_path = osp.join(d_root, f_name)
            res[osp.relpath(f_path, hugo_site_public)] = f_hash(f_path)

    return res


def get_remote_meta(client, hugo_site_root: str) -> Dict[str, str]:
    try:
        response = client.get_object(Bucket=BUCKET_NAME, Key=".meta.json")
        body = response["Body"].read()
        meta = json.loads(body)
    except botocore.exceptions.ClientError as error:
        code = error.response["Error"]["Code"]
        if code in ("NoSuchKey", "404"):
            meta = {}
        else:
            raise error
    return meta


def incremental_update(
    client,
    hugo_site_root: str,
    remote_meta: Dict[str, str],
    local_meta: Dict[str, str],
    dry_run: bool,
    ignore_remote_meta: bool,
):
    # delete
    del_list = []
    for obj_name in remote_meta:
        if obj_name not in local_meta:
            if obj_name == ".meta.json":
                continue
            del_list.append(obj_name)
    if len(del_list) > 0:
        if not dry_run:

            def _del_obj(obj_name: str) -> dict:
                return {
                    "Key": obj_name,
                }

            del_list = list(map(_del_obj, del_list))
            results = client.delete_objects(
                Bucket=BUCKET_NAME, Delete={"Objects": del_list}
            )
            for d in results["Deleted"]:
                print(f"Deleted: {d['Key']}")
            if "Errors" in results:
                for e in results["Errors"]:
                    print(f"Error {e['Code']}: {e['Message']}")
        else:
            print("Will delete these files in remote:")
            for obj_name in del_list:
                print(obj_name)
    # update
    hugo_site_public = osp.join(hugo_site_root, "public")
    print(f"Will upload: ")
    for obj_name in local_meta:
        need_upload = (obj_name not in remote_meta) or (
            remote_meta[obj_name] != local_meta[obj_name]
        )
        if ignore_remote_meta:
            need_upload = True
        if not need_upload:
            continue
        local_f_path = osp.join(hugo_site_public, obj_name)
        print(f"  {local_f_path} -> {obj_name}")
        if not dry_run:
            content_type = "application/octet-stream"
            content_disposition = "inline"
            if obj_name.endswith(".html"):
                content_type = "text/html"
            if obj_name.endswith(".xml"):
                content_type = "text/xml"
            if obj_name.endswith(".js"):
                content_type = "application/javascript; charset=utf-8"
                content_disposition = ""
            if obj_name.endswith(".css"):
                content_type = "text/css"
            with open(local_f_path, "rb") as f:
                client.put_object(
                    Bucket=BUCKET_NAME,
                    Key=obj_name,
                    Body=f.read(),
                    ContentType=content_type,
                    ContentDisposition=content_disposition,
                )
    if not dry_run:
        print("Updating remote meta...")
        client.put_object(
            Bucket=BUCKET_NAME, Key=".meta.json", Body=json.dumps(local_meta).encode()
        )


def main():
    cwd = os.getcwd()
    hugo_site_root = osp.join(cwd, "hugo-site")
    if not osp.exists(hugo_site_root):
        print(f"Cannot find `hugo-site` dir in {cwd}")
        sys.exit(0)
    hugo_site_root = osp.abspath(hugo_site_root)
    print(f"Hugo site root: {hugo_site_root}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    parser.add_argument(
        "--ignore-remote-meta",
        dest="ignore_remote_meta",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    dry_run = args.dry_run
    ignore_remote_meta = args.ignore_remote_meta

    print(f"Connecting remote bucket...")
    client = boto3.client(
        service_name="s3",
        endpoint_url=END_POINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(s3={"addressing_style": "virtual", "signature_version": "s3v4"}),
    )

    print(f"Reading local metadata...")
    local_meta = get_local_meta(hugo_site_root=hugo_site_root)
    print(f"Reading remote metadata...")
    remote_meta = get_remote_meta(client=client, hugo_site_root=hugo_site_root)
    print(f"Incremental updating...")
    incremental_update(
        client=client,
        hugo_site_root=hugo_site_root,
        remote_meta=remote_meta,
        local_meta=local_meta,
        dry_run=dry_run,
        ignore_remote_meta=ignore_remote_meta,
    )


if __name__ == "__main__":
    main()
