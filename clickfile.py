#!/usr/bin/env python3
import click
import importlib


@click.group()
def cli():
    pass


class Command(click.Command):
    def __init__(self, module_name, attr_name, cmd_name=None):
        self.module_name = module_name
        self.attr_name = attr_name
        self._resolved = None
        name = cmd_name or attr_name
        super().__init__(name)

    def _load(self):
        if self._resolved is None:
            mod = importlib.import_module(self.module_name)
            self._resolved = getattr(mod, self.attr_name)
        return self._resolved

    def invoke(self, ctx):
        return self._load().invoke(ctx)

    def get_help(self, ctx):
        return self._load().get_help(ctx)

    def get_params(self, ctx):
        return self._load().get_params(ctx)


class Group(click.Group):
    def __init__(self, module_name, attr_name, cmd_name=None):
        self.module_name = module_name
        self.attr_name = attr_name
        self._resolved = None
        name = cmd_name or attr_name
        super().__init__(name)

    def _load(self):
        if self._resolved is None:
            mod = importlib.import_module(self.module_name)
            self._resolved = getattr(mod, self.attr_name)
        return self._resolved

    def get_command(self, ctx, cmd_name):
        return self._load().get_command(ctx, cmd_name)

    def list_commands(self, ctx):
        return self._load().list_commands(ctx)

    def invoke(self, ctx):
        return self._load().invoke(ctx)

    def get_help(self, ctx):
        return self._load().get_help(ctx)

    def get_params(self, ctx):
        return self._load().get_params(ctx)


def command(module_name: str, attr_name: str, cmd_name: str = None):

    def load_type():
        try:
            mod = importlib.import_module(module_name)
            obj = getattr(mod, attr_name)
            return isinstance(obj, click.Group)
        except Exception:
            return False

    if load_type():
        return Group(module_name, attr_name, cmd_name)
    else:
        return Command(module_name, attr_name, cmd_name)


cli.add_command(command("cli.commands.allure", "allure_cli"), name="allure")
cli.add_command(command("cli.commands.slack", "send_notification"), name="send-notification")
cli.add_command(command("cli.commands.infra", "infra"), name="infra")
cli.add_command(command("cli.commands.dapps", "dapps"), name="dapps")

cli.add_command(command("cli.commands.common", "oz"), name="oz")
cli.add_command(command("cli.commands.common", "run"), name="run")
cli.add_command(command("cli.commands.common", "update_contracts"), name="update-contracts")

cli.add_command(command("cli.commands.load", "locust"), name="locust")
cli.add_command(command("cli.commands.load", "k6"), name="k6")

if __name__ == "__main__":
    cli()
