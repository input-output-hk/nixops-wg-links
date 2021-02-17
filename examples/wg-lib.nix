pkgs: machineList:
let
  inherit (pkgs) lib;
  inherit (lib) filter listToAttrs nameValuePair traceValFn;
  inherit (builtins) toJSON;
in rec {
  enable = true;

  # The wgLib topology can be set to mesh or star.
  # This line determines which will be selected.
  cfg = mesh;
  # cfg = star;

  # For a star topology, define the hub machine
  hub = "machine1";

  # These are wgKeypair attributes that are set to their defaults.
  # They can be overriden for the whole group by editing here,
  # or an individual wgKeypair basis by a recursiveUpdate in the
  # nix deployment file.
  addNoWgHosts = true;
  baseIpv4 = {
    a = 10;
    b = 0;
    c = 0;
    d = 1;
  };
  dns = [ ];
  interfaceName = "nixops-wg0";
  listenPort = 51820;
  mtu = null;
  persistentKeepalive = 25;
  postDown = "";
  postUp = "";
  preDown = "";
  preUp = "";
  syncState = false;
  table = null;
  usePresharedKey = true;

  # Topology set up functions
  mesh = name: filter (m: name != m) machineList;
  star = name: if name == hub then (mesh name) else [ hub ];
  topo = name: cfg:
    traceValFn (x: "wg-links for ${name}: ${toJSON x}") (cfg name);

  # Generic wireguard keypair setup
  wgKeypairGeneric = listToAttrs (map (m:
    nameValuePair "${m}-wg" {
      inherit addNoWgHosts baseIpv4 dns enable interfaceName listenPort mtu
        persistentKeepalive postDown postUp preDown preUp syncState table
        usePresharedKey;
    }) machineList);
}
