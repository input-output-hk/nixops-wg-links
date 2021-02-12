{ sources ? import nix/sources.nix
, overlay ? import (sources.poetry2nix + "/overlay.nix")
, pkgs ? import sources.nixpkgs { overlays = [ overlay ]; } }: {
  nixops-wg-links =
    pkgs.lib.genAttrs [ "x86_64-linux" "i686-linux" "x86_64-darwin" ] (system:
      let
        pkgs = import sources.nixpkgs { inherit system; };
        nixops-wg-links = import ./default.nix { };
      in nixops-wg-links);
}
