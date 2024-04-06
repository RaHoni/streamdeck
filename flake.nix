{
  description = "A possibletie to controll obs from a streamdeck";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      pkgs = import nixpkgs {
        system = "x86_64-linux";
      };
    in
    {

      packages.x86_64-linux = with pkgs.python3Packages; rec {
        streamdeck-obs = buildPythonApplication {
        pname = "streamdeck-obs";
        version = "1.0";

        meta.mainProgram = "streamdeck.py";

        propagatedBuildInputs = [ streamdeck setuptools simpleobsws pillow tkinter ];

        src = ./.;

        doCheck = false;

        };

        simpleobsws = buildPythonApplication rec {
          pname = "simpleobsws";
          version = "1.4.0";
          
          propagatedBuildInputs = [ websockets msgpack ];

          src = fetchPypi {
            inherit pname version;
            hash = "sha256-Ks67BUtFdPeLaU3nuqz3xkmejtxCOmguRG6OXDRDjWg=";
          };

          doCheck = false;
        };

        default = streamdeck-obs;
      };

    };
}
