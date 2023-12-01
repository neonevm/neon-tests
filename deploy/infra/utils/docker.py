import dataclasses
import functools
import json
import pathlib
import re
import typing as tp

import clickfile
from deploy.infra.utils import env

IMAGE_PREFIX = "neonevm"


class Dockerfile:
    def __init__(self, path: str):
        self.path = path

    @property  # type: ignore
    @functools.lru_cache()
    def from_(self) -> str:
        for line in open(self.path).readlines():
            m = re.search(r"FROM\s*(.*)", line)
            if m:
                return m.group(1)
        raise Exception(f"No declaration FROM in dockerfile {self.path}")

    @property  # type: ignore
    @functools.lru_cache()
    def context(self) -> str:
        for line in open(self.path).readlines():
            m = re.search(r"^#\s*context=(.*)", line)
            if m:
                return m.group(1)
        return clickfile.HOME_DIR


@dataclasses.dataclass()
class Image:
    dockerfile: tp.Union[pathlib.Path, Dockerfile]
    name: tp.Optional[str] = None
    tag_name: tp.Optional[str] = None
    prefix: tp.Optional[str] = IMAGE_PREFIX

    def __post_init__(self):
        if isinstance(self.dockerfile, pathlib.Path):
            self.dockerfile = Dockerfile((clickfile.HOME_DIR / self.dockerfile).as_posix())

    @property
    def tag(self) -> str:
        return f"{self.prefix}/{self.name}:{self.tag_name}"

    def build(self, **kwargs) -> None:
        kwargs.setdefault("tag", self.tag)
        docker_build(self.dockerfile, **kwargs)

    def __str__(self) -> str:
        return self.tag


@functools.lru_cache()
def docker_build(
        dockerfile: Dockerfile,
        tag: tp.Optional[str] = None,
        cache: bool = True,
        build_args: tp.Optional[tp.Tuple[tp.Tuple[str, str]]] = None,
):
    pull_image = not tp.cast(str, dockerfile.from_).startswith(IMAGE_PREFIX)

    def var_args():
        args = [
            f"-t {tag}" if tag else None,
            "--no-cache" if not cache else None,
            "--pull" if pull_image else None,
        ]
        if build_args:
            args.extend(f"--build-arg {k}={v}" for k, v in build_args)
        return " ".join(filter(None, args))

    env.header("Build {}".format(tag))
    image_before = docker_image_inspect(tag)
    env.shell(
        f"docker build {dockerfile.context}"
        f" -f {dockerfile.path}"
        f" {var_args()}"
    )
    image_after = docker_image_inspect(tag)

    return image_before and image_before["Id"] != image_after["Id"]


def docker_image_inspect(image: str) -> tp.Optional[dict]:
    """Inspect docker image."""
    with env.quiet():
        out = env.shell(f"docker image inspect {image}")
    return json.loads(out)[0] if out else None


def docker_image_exists(image: str) -> bool:
    """Returns True when image exists in a local cache (== pulled).
    It's faster then calling docker inspect.
    """
    return bool(env.shell(f"docker images -q {image}", capture=True))


def docker_inspect(container: str) -> tp.Optional[dict]:
    """Inspect docker container."""
    with env.quiet():
        out = env.shell(f"docker inspect {container}")
    return json.loads(out)[0] if out else None


def docker_inspect_network(network: str) -> tp.Optional[dict]:
    """Inspect docker network."""
    with env.quiet():
        out = env.shell(f"docker network inspect {network}")
    return json.loads(out)[0] if out else None


def docker_pull(image: str) -> bool:
    """Pulls image, returns True if pulled a fresh one."""
    if ":" not in image:
        image = f"{image}:latest"
    return "Status: Downloaded newer image" in env.shell(f"docker pull {image}", tee=True)


def cleanup_docker_networks():
    """Remove test networks that are left after."""
    print(env.header("Cleanup unused docker networks"))
    with env.quiet():
        env.shell("docker network prune -f")


def cleanup_running_containers():
    """Kill and remove long-running medium tests containers."""
    env.header("Cleanup old containers")

    long_running_re = re.compile(r"Up \d+ hours")
    kill_containers = []

    ps_output = env.shell('docker ps --format="{{.Names}} {{.Image}} {{.Status}}"', capture=True)
    for row in ps_output.splitlines():
        container_name, image_name, running_for = row.split(" ", 2)
        if (
            long_running_re.match(running_for)
            # skip DevBox
            and "neonlabs/devbox" not in image_name
        ):
            kill_containers.append(container_name)

    if kill_containers:
        env.pprint_list("Killing containers:", kill_containers, env.yellow)
        env.shell("docker rm -f {}".format(" ".join(kill_containers)))



