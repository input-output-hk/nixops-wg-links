let
  region = "us-east-2"; # Adjust your desired AWS deployment region here
  accessKeyId = "personal"; # Adjust your desired AWS profile name here
in {
  # A simple wireguard links deployment example
  network.description = "aws-wg-simple";

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

    # Each machine participating in the wireguard links plugin requires at a minimum,
    # an attribute of its machine name with `-wg` appended and enable set to true.
    wgKeypair = {
      machine1-wg.enable = true;
      machine2-wg.enable = true;
    };
  };

  machine1 = { resources, config, pkgs, ... }: {
    deployment = {
      targetEnv = "ec2";
      ec2 = {
        inherit region accessKeyId;
        instanceType = "t3.nano";
        keyPair = resources.ec2KeyPairs.awsKey;
        securityGroups = [ resources.ec2SecurityGroups.allowSshWg ];
      };

      # Wireguard links to other machine are specified here
      wgLinksTo = [ "machine2" ];
    };
  };

  machine2 = { resources, config, pkgs, ... }: {
    deployment = {
      targetEnv = "ec2";
      ec2 = {
        inherit region accessKeyId;
        instanceType = "t3.nano";
        keyPair = resources.ec2KeyPairs.awsKey;
        securityGroups = [ resources.ec2SecurityGroups.allowSshWg ];
      };

      # Wireguard links to other machine are specified here
      wgLinksTo = [ "machine1" ];
    };
  };
}
