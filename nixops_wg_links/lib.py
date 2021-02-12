# -*- coding: utf-8 -*-

# Automatic provisioning of wireguard links.

from collections import defaultdict, Counter
from nixops.backends import MachineDefinition, MachineState
from nixops.deployment import Deployment, is_machine
from typing import (
    Any,
    cast,
    DefaultDict,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)
import ipaddress
import logging
import nixops.resources
import nixops.util
import nixops_wg_links.resources
import re
import shlex
import subprocess

logger = logging.getLogger(__name__)


def findWgKeypair(
    self: MachineState, name: str
) -> Optional[nixops_wg_links.resources.wg_keypair.WgKeypairState]:

    for r in self.depl.active_resources.values():
        if isinstance(r, nixops_wg_links.resources.wg_keypair.WgKeypairState):
            wg_keypair = cast(nixops_wg_links.resources.wg_keypair.WgKeypairState, r)
            if wg_keypair.name == name:
                return wg_keypair
    return None


def upload_wg_keypair(
    self: MachineState, interface_name: str, private: str, public: str, psk: str
) -> None:

    # Upload the key state
    res = self.run_command(
        "umask 077 && mkdir -p /etc/nixops-wg-links && "
        + f'echo "{private}" > /etc/nixops-wg-links/wireguard.private && '
        + f'echo "{public}" > /etc/nixops-wg-links/wireguard.public && '
        + f'echo "{psk}" > /etc/nixops-wg-links/wireguard.psk',
        check=False,
    )
    if res != 0:
        raise Exception(f"unable to save wireguard keys to ‘{self.name}’")

    # Stop the wireguard service if running to ensure proper keys will be used upon nixos activation
    res = self.run_command(
        f"if systemctl is-active --quiet wg-quick-{interface_name}.service; then "
        + f"systemctl stop wg-quick-{interface_name}.service || exit 1; "
        + "else exit 0; "
        + "fi",
        check=False,
    )
    if res != 0:
        raise Exception(
            f"unable to stop wg-quick-{interface_name}.service on ‘{self.name}’ after uploading wireguard keys"
        )


def create_wg_keypair(wg_path: str) -> Tuple[str, str, str]:

    try:
        keypair = subprocess.run(
            f'PRV="$({shlex.quote(wg_path)} genkey)" && '
            + f'PUB="$({shlex.quote(wg_path)} pubkey <<< "$PRV")" && '
            + f'PSK="$({shlex.quote(wg_path)} genpsk)" && '
            + 'echo "$PRV $PUB $PSK"',
            shell=True,
            check=False,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        raise Exception(
            f"wireguard key generation failed with error: ‘{keypair.stderr}’"
        )

    if keypair.returncode != 0:
        raise Exception(
            f"wireguard key generation failed with error: ‘{keypair.stderr}’"
        )

    keypair_list = keypair.stdout.split()
    private = keypair_list[0]
    public = keypair_list[1]
    psk = keypair_list[2]
    return (private, public, psk)


def get_wg_path() -> str:

    wg_path = nixops.util.which("wg")
    if not wg_path:
        raise Exception(
            'the wireguard tool "wg" must be available in the system path of the deployer for key generation; please install and try again'
        )
    return wg_path


def generate_wg_keypair(self: MachineState) -> None:

    defn = to_wg_links_defn(self.defn)

    # Only generate keys for which there is a wgLinksTo nix definition
    if len(defn.wgLinksTo) == 0:
        return

    wg_path = get_wg_path()
    wg_keypair = findWgKeypair(self, f"{self.name}-wg")
    if not wg_keypair:
        raise Exception(f"wireguard link resource not found for ‘{self.name}’")

    if not wg_keypair.private or not wg_keypair.public or not wg_keypair.psk:
        # If the wireguard keypair does not yet exist yet,
        # create, upload and save in nixops state
        logger.debug(f"Creating wireguard keypair state for ‘{self.name}’")
        (private, public, psk) = create_wg_keypair(wg_path)
        upload_wg_keypair(
            self,
            wg_keypair.interface_name,
            private.strip(),
            public.strip(),
            psk.strip(),
        )
        wg_keypair.private = private.strip()
        wg_keypair.public = public.strip()
        wg_keypair.psk = psk.strip()
    elif wg_keypair.sync_state:
        # If a sync_state has been requested, repush
        upload_wg_keypair(
            self,
            wg_keypair.interface_name,
            wg_keypair.private,
            wg_keypair.public,
            wg_keypair.psk,
        )


class WgLinksDefinition(MachineDefinition):
    """Definition of Wg Links."""

    wgLinksTo: Set[str]

    @classmethod
    def get_type(cls):
        return "wg-links"

    def __init__(self, name: str, config):
        super().__init__(name, config)


class WgLinksState(MachineState[WgLinksDefinition]):
    """State of Wg Links."""

    definition_type = WgLinksDefinition

    @classmethod
    def get_type(cls):
        return "wg-links"


def index_to_private_ip(wg_keypair: nixops_wg_links.resources.wg_keypair.WgKeypairState, index: int) -> str:

    a_base = wg_keypair.base_ipv4["a"]
    b_base = wg_keypair.base_ipv4["b"]
    c_base = wg_keypair.base_ipv4["c"]
    d_base = wg_keypair.base_ipv4["d"]

    try:
        base_addr = ipaddress.IPv4Address(f"{a_base}.{b_base}.{c_base}.{d_base}")
    except ValueError:
        raise ValueError(f"base ipv4 wireguard address {base_addr} for ‘{wg_keypair.name}’ is invalid")

    if not base_addr.is_private:
        raise ValueError(f"base ipv4 wireguard address {base_addr} for ‘{wg_keypair.name}’ is not a private ipv4 address")

    d = (d_base + index) % 256
    d_r = (d_base + index) // 256
    c = (c_base + d_r) % 256
    c_r = (c_base + d_r) // 256
    b = (b_base + c_r) % 256
    b_r = (b_base + c_r) // 256
    a = (a_base + b_r) % 256

    try:
        addr = ipaddress.IPv4Address(f"{a}.{b}.{c}.{d}")
    except ValueError:
        raise ValueError(f"generated wireguard address {addr} for ‘{wg_keypair.name}’ is invalid")

    if not addr.is_private:
        raise ValueError(f"generated wireguard address {addr} for ‘{wg_keypair.name}’ is not a private ipv4")

    return addr.exploded


def to_wg_links_defn(d: Optional[MachineDefinition]) -> WgLinksDefinition:

    if d:
        e = WgLinksDefinition(d.name, d.resource_eval)
        e.wgLinksTo = d.resource_eval["wgLinksTo"]
        return e
    else:
        raise TypeError("defn was None")


def mk_matrix(d: Deployment) -> Dict[str, List[Dict[Tuple[str, ...], Any]]]:

    self = d

    active_machines = self.active_machines
    active_resources = self.active_resources

    attrs_per_resource: Dict[str, List[Dict[Tuple[str, ...], Any]]] = {
        m.name: [] for m in active_resources.values()
    }

    hosts: DefaultDict[str, DefaultDict[str, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )

    total_peers: Dict[str, List[Any]] = {m.name: [] for m in active_machines.values()}

    wg_keypair_list: Dict[str, nixops_wg_links.resources.wg_keypair.WgKeypairState] = {}
    wg_psk: Dict[str, str] = {}
    wg_name: Dict[str, str] = {}

    for m in active_machines.values():
        wg_keypair = findWgKeypair(m, f"{m.name}-wg")
        if wg_keypair:
            wg_keypair_list[m.name] = wg_keypair
            wg_psk[m.name] = wg_keypair.psk
            wg_name[m.name] = wg_keypair.name

    if any(wg_psk.values()):
        psk, count = Counter(wg_psk.values()).most_common(1)[0]
        if count == len(wg_psk):
            logger.debug("wireguard preshared keys match in nixops state")
        else:
            for m in active_machines.values():
                # Sync key state if m is up, included, public ip is available and psk is not in sync
                if (m.state == m.UP) and m.defn and m.public_ipv4 and wg_keypair_list[m.name].psk != psk:
                    upload_wg_keypair(
                        m,
                        wg_keypair_list[m.name].interface_name,
                        wg_keypair_list[m.name].private,
                        wg_keypair_list[m.name].public,
                        psk,
                    )
                    wg_keypair_list[m.name].psk = psk

    def do_machine(m: nixops.backends.MachineState) -> None:
        # Skip configuration if the machine is excluded or the associated wgKeypair is not up yet
        if not m.defn or m.name not in wg_keypair_list or (wg_keypair_list[m.name].state != wg_keypair_list[m.name].UP):
            return

        wg_local_ipv4 = index_to_private_ip(wg_keypair_list[m.name], m.index)
        defn = to_wg_links_defn(m.defn)

        # Emit configuration to realise wg peer-to-peer links.
        for r2 in active_resources.values():
            ip = m.address_to(r2)
            if ip and wg_keypair_list[m.name].add_no_wg_hosts:
                hosts[m.name][ip] += [r2.name + "-nowg"]

        for m2_name in defn.wgLinksTo:
            m2 = active_machines[m2_name]

            # Skip configuration of target machines the associated wgKeypair is not up yet
            if wg_keypair_list[m2.name].state != wg_keypair_list[m2.name].UP:
                continue

            # Assert the wg-link target exists
            if m2.name not in active_machines:
                raise Exception(
                    f"‘deployment.wgLinksTo’ in machine ‘{m.name}’ refers to an unknown machine ‘{m2.name}’"
                )

            # Assert the wg-link doesn't have the same machine at both ends
            if m2.name == m.name:
                raise Exception(
                    f"‘deployment.wgLinksTo’ in machine ‘{m.name}’ refers to itself ‘{m2.name}’"
                )

            # Assert both machine endpoints have an index required for generating a wireguard address
            if not isinstance(m.index, int):
                raise ValueError(
                    f"‘{m.name}’ is missing an optional index required for wg-links"
                )
            if not isinstance(m2.index, int):
                raise ValueError(
                    f"‘{m2.name}’ is missing an optional index required for wg-links"
                )

            # Assert that reciprocal wg links are specified
            if (
                m.name
                not in to_wg_links_defn(
                    self._machine_definition_for_required(m2.name)
                ).wgLinksTo
            ):
                raise ValueError(
                    f"‘{m.name}’ specifies a wg link to ‘{m2.name}’, "
                    + f"but ‘{m2.name}’ does not specify a wg link to ‘{m.name}’"
                    + "and it must for a complete wg-link"
                )

            # Assert that both machine endpoints agree on the use of a preshared key
            if wg_keypair_list[m.name].use_psk != wg_keypair_list[m2.name].use_psk:
                raise ValueError(
                    f"‘{m.name}’ (usePresharedKey = {wg_keypair_list[m.name].use_psk}) and "
                    + f"‘{m2.name}’ (usePresharedKey = {wg_keypair_list[m2.name].use_psk}) do not"
                    + "agree on the use of a preshared key, but they must for a functional wg-link"
                )

            # Assert that both machine endpoints agree on the preshared key using one
            if wg_keypair_list[m.name].use_psk and (wg_keypair_list[m.name].psk != wg_keypair_list[m2.name].psk):
                raise ValueError(
                    f"‘{m.name}’ and ‘{m2.name}’ do not agree on the preshared key"
                )

            wg_remote_ipv4 = index_to_private_ip(wg_keypair_list[m2.name], m2.index)

            # Assert that both machine endpoints don't have an ipv4 collision due to base_ipv4 skew
            if wg_local_ipv4 == wg_remote_ipv4:
                raise ValueError(
                    f"‘{m.name}’ (addr = {wg_local_ipv4}) and ‘{m2.name}’ (addr = {wg_remote_ipv4}) "
                    + "have been assigned the same wireguard address.  This can happen by chance if "
                    + "the wg-link for each machine has a different baseIpv4 addresses.  It is recommended "
                    + "to use a single baseIpv4 address for a full deployment."
                )

            total_peers[m.name].append(
                {
                    "publicKey": wg_keypair_list[m2.name].public,
                    "allowedIPs": [f"{wg_remote_ipv4}/32"],
                    "endpoint": f"{m2.public_ipv4}:{wg_keypair_list[m2.name].listen_port}",
                    "persistentKeepalive": wg_keypair_list[m.name].keepalive
                    if 1 <= (wg_keypair_list[m.name].keepalive or 0) <= 65535
                    else None,
                    "presharedKeyFile": "/etc/nixops-wg-links/wireguard.psk"
                    if wg_keypair_list[m.name].use_psk
                    else None,
                }
            )

            hosts[m.name][wg_remote_ipv4] += [m2.name + "-wg"]

        # Always use the wg/nowg suffixes for aliases
        wg_keypair_list[m.name].addr = wg_local_ipv4
        hosts[m.name]["127.0.0.1"].append(m.name)
        hosts[m.name][wg_local_ipv4].append(m.name + "-wg")

    for m in active_machines.values():
        do_machine(m)

    def emit_resource(r: nixops.resources.ResourceState) -> None:
        config = attrs_per_resource[r.name]
        if is_machine(r):
            # Skip resource emission if the machine is excluded or the associated wgKeypair is not up yet
            if not r.defn or r.name not in wg_keypair_list or (wg_keypair_list[r.name].state != wg_keypair_list[r.name].UP):
                return

            # Sort the hosts by its canonical host names.
            sorted_hosts = sorted(hosts[r.name].items(), key=lambda item: item[1][0])

            # Just to remember the format:
            #   ip_address canonical_hostname [aliases...]
            extra_hosts = {f"{ip}": names for ip, names in sorted_hosts}

            # Add the base wireguard nix config for machine m
            wg_local_ipv4 = index_to_private_ip(wg_keypair_list[r.name], r.index)

            # Substitute wireguard IPs for any wg-link resources name in the dns list
            if wg_keypair_list[r.name].dns != []:
                dns_list = cast(List[str], wg_keypair_list[r.name].dns).copy()
                for i, dns in enumerate(wg_keypair_list[r.name].dns):
                    if dns in wg_name.values():
                        del dns_list[i]
                        dns_list.insert(
                            i,
                            index_to_private_ip(
                                wg_keypair_list[re.sub("-wg$", "", dns)],
                                active_machines[re.sub("-wg$", "", dns)].index
                            ),
                        )
            else:
                dns_list = []

            config.append(
                {
                    ("networking", "hosts"): extra_hosts,
                    ("networking", "firewall", "allowedUDPPorts"): [
                        wg_keypair_list[r.name].listen_port
                    ],
                    (
                        "networking",
                        "wg-quick",
                        "interfaces",
                        wg_keypair_list[r.name].interface_name,
                    ): {
                        "address": [f"{wg_local_ipv4}/24"],
                        "listenPort": wg_keypair_list[r.name].listen_port,
                        "privateKeyFile": "/etc/nixops-wg-links/wireguard.private",
                        "dns": dns_list,
                        "mtu": wg_keypair_list[r.name].mtu
                        if (wg_keypair_list[r.name].mtu or 0) >= 1
                        else None,
                        "preUp": wg_keypair_list[r.name].pre_up,
                        "preDown": wg_keypair_list[r.name].pre_down,
                        "postUp": wg_keypair_list[r.name].post_up,
                        "postDown": wg_keypair_list[r.name].post_down,
                        "table": wg_keypair_list[r.name].table,
                    },
                    (
                        "networking",
                        "wg-quick",
                        "interfaces",
                        wg_keypair_list[r.name].interface_name,
                        "peers",
                    ): total_peers[r.name],
                }
            )

    for r in active_resources.values():
        emit_resource(r)

    return attrs_per_resource
