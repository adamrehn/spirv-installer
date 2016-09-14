#!/usr/bin/env sh

# Ensure this script is run as root
if [ `id -u` -ne 0 ]; then
	echo "Error: this script must be run as root!"
	exit
fi

# The installation locations for the SPIR-V tools and the wrappers/symlinks
export SPIRVVER=1.1
export SPIRVDIR=/usr/local/spirv/$SPIRVVER
export BINDIR=/usr/local/bin

# Create the installation directories if they don't already exist
test -d "$SPIRVDIR" || mkdir -p "$SPIRVDIR"
test -d "$BINDIR" || mkdir -p "$BINDIR"

# Copy the SPIR-V directory
cp -R ./spirv/$SPIRVVER "$SPIRVDIR/../"

# Process each of the convenience wrappers, filling in the path to spirv-clang
for wrapperFile in ./wrappers/*; do
	wrapperName="$(basename $wrapperFile)"
	sed "s#__SPIRV_DIR__#$SPIRVDIR#g" $wrapperFile > "$BINDIR/$wrapperName"
	chmod 775 "$BINDIR/$wrapperName"
done

# Create symlinks for each of the binaries
for binary in ./spirv/$SPIRVVER/bin/*; do
	binary="$(basename $binary)"
	ln -f -s "$SPIRVDIR/bin/$binary" "$BINDIR/$binary"
done
