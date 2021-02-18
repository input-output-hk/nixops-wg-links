# NixOps Wireguard Plugin

NixOps (formerly known as Charon) is a tool for deploying NixOS machines in a network or cloud.

This repo contains the NixOps Wireguard Plugin.

* [Manual](https://nixos.org/nixops/manual/)
* [Installation](https://nixos.org/nixops/manual/#chap-installation) / [Hacking](https://nixos.org/nixops/manual/#chap-hacking)
* [Continuous build](http://hydra.nixos.org/jobset/nixops/master#tabs-jobs)
* [Source code](https://github.com/NixOS/nixops)
* [Issue Tracker](https://github.com/NixOS/nixops/issues)
* [Mailing list / Google group](https://groups.google.com/forum/#!forum/nixops-users)
* [IRC - #nixos on freenode.net](irc://irc.freenode.net/#nixos)


## Introduction

* This plugin exists to make [wireguard](https://www.wireguard.com/) links easier between intra-deployment nixops machines.
* This plugin utilizes the `networking.wg-quick.*` options of nixos to configure wireguard.
* With a few lines of nix, mesh or star wireguard link topologies can be quickly deployed.


## Requirements

* This plugin won't work independently -- it needs to be used in nixops along with another plugin that creates nixops machines, such as:
  * [nixops-aws](https://github.com/NixOS/nixops-aws/)
  * [or other plugins](https://github.com/input-output-hk/nixops-flake#repo-urls-for-the-plugins-referenced-above)

* The machine used to deploy a nixops cluster utilizing this plugin must have the `wg` tool available in the system path to ensure:
  * The plugin can run `wg genkey` to generate private wireguard keys.
  * The plugin can run `wg pubkey` to generate public wireguard keys.
  * The plugin can run `wg genpsk` to generate private shared symmetrical encryption wireguard keys.

* If this plugin does not find the `wg` utility in the system path, an exception will be thrown asking for it to be installed.
* For nix or nixos, the `wg` utility is available from the `wireguard-tools` package.


## Quick Start

* If you are running a nix flake enabled machine, you can quickly get a working nixops with this and other plugins bundled together by running:
```bash
nix shell github:input-output-hk/nixops-flake
```

* If you do not yet have a nix flake enabled machine, see the nixops-flake README section on legacy packages [here](https://github.com/input-output-hk/nixops-flake#flake-outputs-and-legacy-packages).


## The Minimum Declarative Configuration

* The minimum declarative configuration required to enable a wireguard link between machines is:
  * Declare one wireguard keypair for each machine which will be involved in a wireguard link and enable it.
  * Name each wireguard keypair after the name of each machine with a suffix of `-wg` added.
  * For example, if two machines are to be configured for wireguard peering, and they are machine1 and machine2, then:
```
  resources.wgKeypair = {
    machine1-wg.enable = true;
    machine2-wg.enable = true;
  };
```
  * Then, in the deployment configuration for each machine, declare which other machines each should be wireguard peered to:
```
  machine1 = { ... }: {
    deployment.wgLinksTo = [ "machine2" ];
  }

  machine2 = { ... }: {
    deployment.wgLinksTo = [ "machine1" ];
  }
```

* A complete "simple" example for an AWS machines can be found [here](examples/aws-wg-simple.nix).


## Advanced Usage

* With just a few more lines of nix, mesh or star wireguard peering topologies can be quickly configured and deployed.
* Custom wireguard configuration options are available through attributes in the `wgKeypair` resource:
  * Options for customizations are found [here](nixops_wg_links/nix/wg-keypair.nix).
* Wireguard customizations can be easily deployed across all wireguard keypair resources, or selectively applied as needed.
* A complete "advanced" example for an AWS machines deployment can be found [here](examples/aws-wg-advanced.nix).
* This advanced example utilizes a small nix wireguard library from [here](examples/wg-lib.nix).


## Hosts File References

* For each wireguard link that is created and added to a machine, the hosts file of that machine will have an added entry to the target peer machine with a `-wg` appended.
* If the `wgKeypair` resource option `addNoWgHosts` is set to true instead of the default of false, any machines in the cluster without a wireguard peer, will also be added with a `-nowg` appended.



## Recommendations:

* This plugin performs some sanity checks to ensure machines at each end of a wireguard peering link have compatible configurations and will:
  * Check to ensure a machine doesn't try to peer to itself.
  * Check that reciprocal links are specified where each machine must refer to the other to form a valid wireguard link.
  * Check that the machines at each end of a wireguard peer link agree on pre-shared key usage, and if used, pre-shared key value.
  * Check that the machines at each end of a wireguard peer link don't have a collision in assigned wireguard IPv4 address.
* In general, if your configuration for wireguard keypair configurations is kept consistent across a deployment, you shouldn't run into problems.
* The more complicated and inconsistent you might make your configuration, the more likely you may run into a problem outside the scope of the above mentioned sanity checks.
* Therefore, keeping the configuration simple and consistent is recommended.


## Quirks

* If you are nixops deploying machines which don't have the wireguard kernel module already built in, then:
  * After the first deployment, expect to see a systemd service failure due to the missing wireguard kernel module not yet being loaded by the kernel.
  * Reboot the failing machines to load the wireguard kernel module.
  * Expect to see the wireguard links working after the reboot.

* The requirement to name each wireguard keypair after each participating machine with a `-wg` suffix is a little arbitrary:
  * This allowed for faster initial plugin development to an MVP.
  * This requirement may be dropped in the future and instead a wireguard keypair to machine correspondence established by keypair resource attribute instead.


## Troubleshooting

* Each wireguard keypair resource has wireguard keys generated once, deployed to the machine they provide wireguard configuration for and also saved to nixops state.
* To save on time delays for large machine quantity and/or high latency deployment clusters, a state check of keys on each machine is *not* done with each deployment, unless:
  * Nixops is missing local key state for a `wgKeypair` resource.
  * A `wgKeypair` resource has the `syncState` attribute set to true, which will force a key state synchronization and wireguard service restart on each deployment.

* If problems develop, the wireguard keypair resource attributes can be examined by running:
```bash
nixops export -d $DEPLOYMENT
```

* If inconsistent key state is suspected to be a problem, setting `syncState = true` for each `wgKeypair` resource and re-deploying will ensure key state is consistent across the cluster.


## Developing

To build this plugin locally, albeit without any other nixops plugins, you can run:

```bash
  $ nix-shell
  $ poetry install
  $ poetry shell
```
To view active plugins:

```bash
nixops list-plugins
```

For development and testing in conjunction with other nixops plugins, see the suggestions discussed [here](https://github.com/input-output-hk/nixops-flake#development-and-testing).


## Additional Notes and References

* See the nixos wireguard [wiki article](https://nixos.wiki/wiki/Wireguard) for additional wireguard configuration info.
* The python code is formatted with [black](https://black.readthedocs.io/en/stable).
* The python code is type checked with [mypy](https://mypy.readthedocs.io/en/stable/).
* The python code is style checked with [flake8](https://flake8.pycqa.org/en/latest/).
* The nix code is formatted with [nixfmt](https://hackage.haskell.org/package/nixfmt).
* For additional information on nixops and plugins, see the main NixOps [repo](https://github.com/NixOS/nixops) and the Nixops [Read the Docs](https://nixops.readthedocs.io/en/latest/index.html).

