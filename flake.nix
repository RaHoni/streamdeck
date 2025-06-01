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
        version = "1.1";
        pyproject = true;

        meta.mainProgram = "streamdeck-obs";

        nativeBuildInputs = [ pkgs.copyDesktopItems setuptools-scm setuptools ];

        desktopItems = [(pkgs.makeDesktopItem {
          name = "streamdeck";
          desktopName = "Streamdeck";
          exec = "streamdeck-obs";
        })];
        dontCheckRuntimeDeps = true;

        propagatedBuildInputs = [ streamdeck simpleobsws pillow tkinter ];

        src = ./.;

        doCheck = false;

        };

        simpleobsws = buildPythonApplication rec {
          pname = "simpleobsws";
          version = "1.4.2";
          
          propagatedBuildInputs = [ websockets msgpack ];

          src = fetchPypi {
            inherit pname version;
            hash = "sha256-Y2CUyVp4s796mCIfeURJf8sBYB41z2bZLVo4R9kod4s=";
          };

          doCheck = false;
        };

        default = streamdeck-obs;
      };

    };
}
