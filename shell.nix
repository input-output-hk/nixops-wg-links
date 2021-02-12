{ sources ? import nix/sources.nix
, overlay ? import (sources.poetry2nix + "/overlay.nix")
, pkgs ? import sources.nixpkgs { overlays = [ overlay ]; }
}:
let
  poetryEnv = (pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./.;
    overrides = pkgs.poetry2nix.overrides.withDefaults overlay;
  });
in pkgs.mkShell {
  buildInputs = with pkgs; [
    black
    mypy
    nixfmt
    poetry
    python3
    python3Packages.flake8
  ];
}
