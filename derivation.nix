{ lib, python3Packages }:
python3Packages.buildPythonApplication {
  pname = "streamdeck-obs";
  version = "1.0";
  propagatedBuildInputs = [ python3Packages.streamdeck python3Packages.setuptools  ];

  src = ./.;

}
