import typing as tp
import pathlib


def create_allure_environment_opts(opts: dict, dst: tp.Optional[pathlib.Path] = None):
    if dst is None:
        dst = pathlib.Path() / "allure-results" / "environment.properties"
    with open(dst, "a+") as file:
        file.write(
            "\n".join(
                map(
                    lambda x: f"{x[0]}={x[1] if x[1] and len(x[1]) > 0 else 'empty value'}",
                    opts.items(),
                )
            )
        )
        file.write("\n")
