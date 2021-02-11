import os.path
import nixops.plugins
from nixops.deployment import Deployment
from nixops.backends import MachineState
from nixops.plugins import Plugin, MachineHooks, DeploymentHooks

from .lib import generate_wg_keypair
from .lib import mk_matrix


class WgLinksMachineHooks(MachineHooks):
    def post_wait(self, m: MachineState) -> None:
        generate_wg_keypair(m)


class WgLinksDeploymentHooks(DeploymentHooks):
    def physical_spec(self, d: Deployment):
        return mk_matrix(d)


class NixopsWgLinksPlugin(Plugin):
    def __init__(self):
        self._deployment_hooks = WgLinksDeploymentHooks()
        self._machine_hooks = WgLinksMachineHooks()

    def deployment_hooks(self) -> WgLinksDeploymentHooks:
        return self._deployment_hooks

    def machine_hooks(self) -> WgLinksMachineHooks:
        return self._machine_hooks

    @staticmethod
    def nixexprs():
        return [os.path.dirname(os.path.abspath(__file__)) + "/nix"]

    @staticmethod
    def load():
        return ["nixops_wg_links.resources.wg_keypair"]


@nixops.plugins.hookimpl
def plugin():
    return NixopsWgLinksPlugin()
