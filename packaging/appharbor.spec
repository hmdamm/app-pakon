Name:           appharbor
Version:        0.1.0
Release:        1%{?dist}
Summary:        Universal Linux Application Manager

License:        MIT
URL:            https://github.com/hmdamm/app-pakon
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  tar
Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita

%description
AppHarbor is an open-source desktop application that provides a unified,
transparent inventory of installed applications across Flatpak, RPM/DNF,
Snap, AppImage, and manual desktop entries, featuring safe and explicit
uninstallation workflows.

%prep
%autosetup -n %{name}-%{version}

%build
# Pure python package, files installed directly

%install
rm -rf "%{buildroot}"
mkdir -p "%{buildroot}%{_bindir}"
mkdir -p "%{buildroot}%{_datadir}/applications"
mkdir -p "%{buildroot}%{_datadir}/metainfo"
mkdir -p "%{buildroot}%{_datadir}/icons/hicolor/scalable/apps"
mkdir -p "%{buildroot}%{_prefix}/lib/appharbor"

# Install application python modules
cp -r appharbor "%{buildroot}%{_prefix}/lib/appharbor/"

# Launcher executable script
cat << 'EOF' > "%{buildroot}%{_bindir}/appharbor"
#!/bin/bash
export PYTHONPATH="/usr/lib/appharbor:${PYTHONPATH:-}"
exec python3 -m appharbor "$@"
EOF
chmod 0755 "%{buildroot}%{_bindir}/appharbor"

# Desktop integration files
install -D -m 0644 data/io.github.appharbor.AppHarbor.desktop "%{buildroot}%{_datadir}/applications/io.github.appharbor.AppHarbor.desktop"
install -D -m 0644 data/io.github.appharbor.AppHarbor.metainfo.xml "%{buildroot}%{_datadir}/metainfo/io.github.appharbor.AppHarbor.metainfo.xml"
install -D -m 0644 data/icons/io.github.appharbor.AppHarbor.svg "%{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.appharbor.AppHarbor.svg"

%files
%license LICENSE
%doc README.md
%{_bindir}/appharbor
%{_prefix}/lib/appharbor/
%{_datadir}/applications/io.github.appharbor.AppHarbor.desktop
%{_datadir}/metainfo/io.github.appharbor.AppHarbor.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/io.github.appharbor.AppHarbor.svg

%changelog
* Thu Oct 15 2026 AppHarbor Contributors <support@appharbor.org> - 0.1.0-1
- Initial public release for app-pakon
