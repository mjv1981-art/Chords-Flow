#!/usr/bin/env bash
set -euo pipefail

# The dev-container is Debian. Its unrelated third-party repositories can have
# expired signing keys; use only the official archives for these Debian packages.
source /etc/os-release
if [ "${ID:-}" != debian ] || [[ ! ${VERSION_CODENAME:-} =~ ^[a-z]+$ ]]; then
  echo 'Expected the Debian Codespaces image. Rebuild the container using .devcontainer/devcontainer.json.' >&2
  exit 1
fi

apt_dir=$(mktemp -d)
trap 'rm -rf "$apt_dir"' EXIT
chmod 755 "$apt_dir"
cat >"$apt_dir/debian.sources" <<EOF
Types: deb
URIs: http://deb.debian.org/debian
Suites: $VERSION_CODENAME $VERSION_CODENAME-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: http://deb.debian.org/debian-security
Suites: $VERSION_CODENAME-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF
chmod 644 "$apt_dir/debian.sources"
apt_options=(
  -o "Dir::Etc::sourcelist=$apt_dir/debian.sources"
  -o 'Dir::Etc::sourceparts=-'
  -o 'APT::Get::List-Cleanup=0'
  -o 'APT::Update::Error-Mode=any'
)
sudo -n apt-get "${apt_options[@]}" update
sudo -n apt-get "${apt_options[@]}" install -y ffmpeg python3-venv
