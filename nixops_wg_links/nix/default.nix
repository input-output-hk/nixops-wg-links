{
  config_exporters = { optionalAttrs, ... }:
    [ (config: { wgLinksTo = config.deployment.wgLinksTo; }) ];

  options = [ ./options.nix ];

  resources = { evalResources, zipAttrs, resourcesByType, ... }: {
    wgKeypair = evalResources ./wg-keypair.nix
      (zipAttrs resourcesByType.wgKeypair or [ ]);
  };

}
