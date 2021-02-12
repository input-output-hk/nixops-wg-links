{ config, pkgs, lib, utils, ... }:
let
  inherit (lib) types;
  cfg = config.deployment.wgLinksTo;
in {
  options = {
    deployment.wgLinksTo = lib.mkOption {
      default = [ ];
      type = types.listOf types.str;
      description = ''
        NixOps will set up encrypted wireguard links to the
        machines listed here.  To generate a complete link, it is
        necessary to set this option on both endpoints.  NixOps will
        set up <filename>/etc/hosts</filename> so that the host names
        of the machines listed here with a "-wg" appended will
        resolve to the addresses of the wireguard link.
      '';
    };
  };
}
