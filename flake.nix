{
  description = "Dev environment with mosquitto, python, and digi-xbee";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { nixpkgs, ... }:
    let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      python = pkgs.python313;
      pythonPackages = python.pkgs;
    in
    {
      devShells.x86_64-linux.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          mosquitto
          python
          pythonPackages.digi-xbee
          pythonPackages.xmodem
          socat
          minicom
          screen
          picocom
          cutecom
          gtkterm
        ];
      };
    };
}
