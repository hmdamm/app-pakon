Name:           appharbor
Version:        0.1.0
Release:        1%{?dist}
Summary:        Universal Linux Application Manager

License:        MIT
URL:            https://github.com/appharbor/appharbor
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
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
%autosetup

%build
%py3_build

%install
%py3_install
install -D -m 0644 data/io.github.appharbor.AppHarbor.desktop %{buildroot}%{_datadir}/applications/io.github.appharbor.AppHarbor.desktop
install -D -m 0644 data/io.github.appharbor.AppHarbor.metainfo.xml %{buildroot}%{_datadir}/metainfo/io.github.appharbor.AppHarbor.metainfo.xml
install -D -m 0644 data/icons/io.github.appharbor.AppHarbor.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.appharbor.AppHarbor.svg

%files
%license LICENSE
%doc README.md docs/
%{_bindir}/appharbor
%{python3_sitelib}/appharbor/
%{python3_sitelib}/appharbor-*.egg-info/
%{_datadir}/applications/io.github.appharbor.AppHarbor.desktop
%{_datadir}/metainfo/io.github.appharbor.AppHarbor.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/io.github.appharbor.AppHarbor.svg

%changelog
* Wed Oct 15 2026 AppHarbor Contributors <support@appharbor.org> - 0.1.0-1
- Initial public release
