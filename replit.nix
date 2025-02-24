{pkgs}: {
  deps = [
    pkgs.tk
    pkgs.tcl
    pkgs.qhull
    pkgs.pkg-config
    pkgs.gtk3
    pkgs.gobject-introspection
    pkgs.ghostscript
    pkgs.ffmpeg-full
    pkgs.cairo
    pkgs.glibcLocales
    pkgs.freetype
  ];
}
