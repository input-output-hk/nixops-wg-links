let
  pkgs = import <nixpkgs> { };
  wgLib = import ./wg-lib.nix pkgs machineList;

  inherit (pkgs) lib;
  inherit (lib) listToAttrs nameValuePair range recursiveUpdate;

  region = "us-east-2"; # Adjust your desired AWS deployment region here
  accessKeyId = "personal"; # Adjust your desired AWS profile name here

  machineNumber = 10;
  baseName = "machine";
  baseConfig = { resources, config, pkgs, name, ... }: {
    deployment = {
      targetEnv = "ec2";
      ec2 = {
        inherit region accessKeyId;
        instanceType = "t3.nano";
        keyPair = resources.ec2KeyPairs.awsKey;
        securityGroups = [ resources.ec2SecurityGroups.allowSshWg ];
      };

      # Use the wgLib to configure either a mesh or star topology.
      wgLinksTo = wgLib.topo name wgLib.cfg;
    };
  };
  machines = i:
    listToAttrs
    (map (i: nameValuePair "${baseName}${toString i}" baseConfig) (range 1 i));
  machineList = map (i: "${baseName}${toString i}") (range 1 machineNumber);
in {
  # An advanced wireguard links deployment example
  network.description = "aws-wg-advanced";

  resources = {
    ec2KeyPairs.awsKey = { inherit region accessKeyId; };
    ec2SecurityGroups.allowSshWg = {
      inherit region accessKeyId;
      name = "allowSshWg";
      description = "Allow SSH and Wireguard";
      rules = [
        {
          fromPort = 22;
          toPort = 22;
          sourceIp = "0.0.0.0/0";
          protocol = "tcp";
        }
        {
          fromPort = 51820;
          toPort = 51820;
          sourceIp = "0.0.0.0/0";
          protocol = "udp";
        }
      ];
    };

    # Generate wireguard keypairs based on machineList with parameters from wgLib.
    wgKeypair = wgLib.wgKeypairGeneric;

    # Or customize the wireguard keypairs as needed.
    # wgKeypair = recursiveUpdate wgLib.wgKeypairGeneric {
    #   machine2-wg.syncState = true;
    # };
  };
} // (machines machineNumber)
