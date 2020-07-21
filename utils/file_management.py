import glob
import os
import pathlib
from hashlib import md5


def get_next_name(file_path: str) -> str:
    posix_path = pathlib.Path(file_path)
    counter: int = 1
    new_file_name: str = "{0}/{1}-copy{2}{3}"
    while os.path.isfile(
        new_file_name.format(
            posix_path.parent,
            posix_path.stem,
            counter,
            "".join(posix_path.suffixes),
        )
    ):
        counter += 1
    return new_file_name.format(
        posix_path.parent,
        posix_path.stem,
        counter,
        "".join(posix_path.suffixes),
    )


def manage_duplicate_file(file_path: str):
    posix_path = pathlib.Path(file_path)
    file_base_name: str = "".join(posix_path.stem.split("-copy")[0:-1])
    name_pattern: str = f"{posix_path.parent}/{file_base_name}*"
    old_files: list = glob.glob(name_pattern)
    old_files.remove(file_path)
    current_file_md5: str = md5(open(file_path, "rb").read()).hexdigest()
    for old_file_path in old_files:
        old_file_md5: str = md5(open(old_file_path, "rb").read()).hexdigest()
        if current_file_md5 == old_file_md5:
            os.remove(file_path)
            break
