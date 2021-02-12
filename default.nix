{ sources ? import nix/sources.nix
, overlay ? import (sources.poetry2nix + "/overlay.nix")
, pkgs ? import sources.nixpkgs { overlays = [ overlay ]; }
}:

pkgs.poetry2nix.mkPoetryApplication {
  projectDir = ./.;
  overrides = pkgs.poetry2nix.overrides.withDefaults(self: super: {
    nixops = super.nixops.overrideAttrs(old: {
      buildInputs = old.buildInputs ++ [ self.poetry ];
    });
  });
  doCheck = false;
}
