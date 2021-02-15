{ pkgs }:

self: super: {
  nixops = super.nixops.overridePythonAttrs ({ nativeBuildInputs ? [ ], ... }: {
    nativeBuildInputs = nativeBuildInputs ++ [ self.poetry ];
    format = "pyproject";
  });
}
