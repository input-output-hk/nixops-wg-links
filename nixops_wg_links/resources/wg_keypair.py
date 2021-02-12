# -*- coding: utf-8 -*-

# Automatic provisioning of wireguard keypair resources.

import nixops.util
import nixops.resources
import logging
from typing import Mapping, Optional, Sequence

logger = logging.getLogger(__name__)


class WgKeypairOptions(nixops.resources.ResourceOptions):
    """Definition of wireguard keypair options."""

    name: str
    enable: bool
    dns: Sequence[str]
    mtu: Optional[int]
    listenPort: int
    persistentKeepalive: Optional[int]
    usePresharedKey: bool
    syncState: bool
    interfaceName: str
    table: Optional[str]
    preUp: str
    preDown: str
    postUp: str
    postDown: str
    baseIpv4: Mapping[str, int]
    addNoWgHosts: bool


class WgKeypairDefinition(nixops.resources.ResourceDefinition):
    """Definition of a wireguard keypair resource."""

    config: WgKeypairOptions

    @classmethod
    def get_type(cls) -> str:
        return "wg-keypair"

    @classmethod
    def get_resource_type(cls) -> str:
        return "wgKeypair"

    def __init__(self, name: str, config: nixops.resources.ResourceEval):
        super().__init__(name, config)
        self.kp_name: str = self.config.name
        self.enable: bool = self.config.enable
        self.dns: Sequence[str] = self.config.dns
        self.mtu: Optional[int] = self.config.mtu
        self.listen_port: int = self.config.listenPort
        self.keepalive: Optional[int] = self.config.persistentKeepalive
        self.use_psk: bool = self.config.usePresharedKey
        self.sync_state: bool = self.config.syncState
        self.interface_name: str = self.config.interfaceName
        self.table: Optional[str] = self.config.table
        self.pre_up: str = self.config.preUp
        self.pre_down: str = self.config.preDown
        self.post_up: str = self.config.postUp
        self.post_down: str = self.config.postDown
        self.base_ipv4: Mapping[str, int] = self.config.baseIpv4
        self.add_no_wg_hosts: bool = self.config.addNoWgHosts


class WgKeypairState(nixops.resources.ResourceState[WgKeypairDefinition]):
    """State of a wireguard keypair resource."""

    kp_name: str = nixops.util.attr_property("wgKeypair.name", None, str)
    enable: bool = nixops.util.attr_property("wgKeypair.enable", False, bool)
    dns: Sequence[str] = nixops.util.attr_property("wgKeypair.dns", [], "json")
    mtu: Optional[int] = nixops.util.attr_property("wgKeypair.mtu", None, int)
    addr: str = nixops.util.attr_property("wgKeypair.addr", None, str)
    private: str = nixops.util.attr_property("wgKeypair.private", None, str)
    public: str = nixops.util.attr_property("wgKeypair.public", None, str)
    listen_port: int = nixops.util.attr_property("wgKeypair.listenPort", None, int)
    keepalive: Optional[int] = nixops.util.attr_property(
        "wgKeypair.keepalive", None, int
    )
    use_psk: bool = nixops.util.attr_property("wgKeypair.usePresharedKey", True, bool)
    psk: str = nixops.util.attr_property("wgKeypair.presharedKey", None, str)
    sync_state: bool = nixops.util.attr_property("wgKeypair.syncState", False, bool)
    interface_name: str = nixops.util.attr_property(
        "wgKeypair.interfaceName", None, str
    )
    table: Optional[str] = nixops.util.attr_property("wgKeypair.table", None, str)
    pre_up: str = nixops.util.attr_property("wgKeypair.preUp", "", str)
    pre_down: str = nixops.util.attr_property("wgKeypair.preDown", "", str)
    post_up: str = nixops.util.attr_property("wgKeypair.postUp", "", str)
    post_down: str = nixops.util.attr_property("wgKeypair.postDown", "", str)
    base_ipv4: Mapping[str, int] = nixops.util.attr_property(
        "wgKeypair.baseIpv4", {}, "json"
    )
    add_no_wg_hosts: bool = nixops.util.attr_property(
        "wgKeypair.addNoWgHosts", True, bool
    )

    @classmethod
    def get_type(cls) -> str:
        return "wg-keypair"

    def __init__(self, depl: nixops.deployment.Deployment, name: str, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)

    @property
    def resource_id(self) -> str:
        return self.kp_name

    def get_definition_prefix(self) -> str:
        return "resources.wgKeypair."

    def create(
        self,
        defn: WgKeypairDefinition,
        check: bool,
        allow_reboot: bool,
        allow_recreate: bool,
    ) -> None:
        self.kp_name = f"nixops-{self.depl.uuid}-{defn.name}"
        self.enable = defn.enable
        self.dns = defn.dns
        self.mtu = defn.mtu
        self.listen_port = defn.listen_port
        self.keepalive = defn.keepalive
        self.use_psk = defn.use_psk
        self.sync_state = defn.sync_state
        self.interface_name = defn.interface_name
        self.table = defn.table
        self.pre_up = defn.pre_up
        self.pre_down = defn.pre_down
        self.post_up = defn.post_up
        self.post_down = defn.post_down
        self.base_ipv4 = defn.base_ipv4
        self.add_no_wg_hosts = defn.add_no_wg_hosts

        self.state = self.UP

    def destroy(self, wipe: bool = False) -> bool:
        if not self.depl.logger.confirm(
            f"are you sure you want to destroy wireguard keypair resource (wg-link) ‘{self.name}’?"
        ):
            return False
        if wipe:
            self.warn("wipe is not supported")
        self.log(f"destroying {self.name} (resource id: {self.kp_name})...")
        return True
