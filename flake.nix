{
  description = "mediawiki_matrix_bot flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: nixpkgs.legacyPackages.${system};
    in {
      packages = forAllSystems (system:
        let
          pkgs = pkgsFor system;
        in {
          mediawiki_matrix_bot = pkgs.python3Packages.buildPythonApplication {
            pname = "mediawiki-matrix-bot";
            version = "1.2.0";
            src = ./.;
            pyproject = true;
            build-system = [ pkgs.python3Packages.setuptools ];
            propagatedBuildInputs = with pkgs.python3Packages; [
              matrix-nio docopt aiohttp
            ];
            nativeBuildInputs = with pkgs.python3Packages; [
              mypy
            ];
            checkPhase = ''
              mypy --strict mediawiki_matrix_bot
            '';
          };
          default = self.packages.${system}.mediawiki_matrix_bot;
        });
    };
}
