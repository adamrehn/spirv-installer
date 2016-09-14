#!/usr/bin/env python3
import argparse, os, platform, re, shlex, shutil, stat, subprocess, sys

# Platform-specific constants
if platform.system() == 'Windows':
	BINEXT    = '.exe'
	WRAPEXT   = '.cmd'
	DEVNULL   = 'NUL'
	GENERATOR = 'NMake Makefiles'
else:
	BINEXT    = ''
	WRAPEXT   = ''
	DEVNULL   = '/dev/null'
	GENERATOR = 'Unix Makefiles'

# Writes the contents of a file
def putFileContents(filename, data):
	f = open(filename, 'w', encoding='utf8')
	f.write(data)
	f.close()

# Wrapper for os.makedirs() that deals with the broken behaviour of exist_ok in Python 3.4.0
def makeDirs(d):
	try:
		os.makedirs(d, exist_ok=True)
	except FileExistsError:
		pass

# Escapes a string with shlex.quote(), and force-wraps quotes if they weren't generated
# (Under Windows, we simply wrap the string in double quotes)
def forceQuotes(s):
	if (platform.system() == 'Windows'):
		return '"' + s + '"'
	else:
		quoteChar = "'"
		quoted = shlex.quote(s)
		if quoted[0:1] != quoteChar:
			quoted = quoteChar + quoted + quoteChar
		return quoted

# Determines if a command succeeded
def commandSucceeded(commandArgs, input=None):
	try:
		proc = subprocess.Popen(
			commandArgs,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			stdin=subprocess.PIPE
		)
		(stdout, stderr) = proc.communicate(input.encode('utf-8') if input != None else None)
		return True if (proc.returncode == 0) else False
	except:
		return False

# Determines the C++ compiler that will be used by cmake
def cxxCompiler():
	compiler = subprocess.Popen(
		['cmake', '--system-information', '-G', GENERATOR],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		universal_newlines=True
	)
	(stdout, stderr) = compiler.communicate(None)
	match = re.compile('CMAKE_CXX_COMPILER == "(.+)"\n').findall(stdout)
	
	# If cmake failed to find a C++ compiler, print any generated error message
	if len(match) == 0:
		print(stderr)
		sys.exit(1)

	return match[0]

# Determines if the specified C++ compiler binary is clang
def isClang(compilerBinary):
	compiler = subprocess.Popen(
		[compilerBinary, '--version'],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		universal_newlines=True
	)
	(stdout, stderr) = compiler.communicate(None)
	return (stdout.find('clang') != -1 or stderr.find('clang') != -1)

# Verifies that the specified clang binary doesn't suffer from bug #23381,
# by attempting to compile the test code from <https://llvm.org/bugs/show_bug.cgi?id=23381>
def doesClangSuffer23381(clangBinary):
	return commandSucceeded(
		[clangBinary, '-c', '-x', 'c++', '-', '-o', DEVNULL],
		'struct Z{operator int() const{return 0;}};void f(){const Z z1;const Z z2={};}'
	) == False

# Verifies that the specified command is available, and prints an error if it is not
def errorIfNotAvailable(command, versionFlag='--version'):
	if commandSucceeded([command, versionFlag]) == False:
		print('Error: ' + command + ' is required for the build process.')
		print('Please ensure ' + command + ' is installed and available in the system PATH.')
		sys.exit(1)

# Performs a compilation command, and terminates execution if it fails
def runOrFail(command, cwd=None):
	if (subprocess.call(command, cwd=cwd) != 0):
		print('Error: compilation failed!')
		sys.exit(1)

# Creates a convenience wrapper for an installed binary
def createWrapper(wrapperLocation, sourceBinary, binaryArgs):
	
	# Append the platform-specific extensions to the specified paths
	wrapperLocation = wrapperLocation + WRAPEXT
	sourceBinary = sourceBinary + BINEXT
	
	# Create either a batch file under Windows or a shell script under other platforms
	if platform.system() == 'Windows':
		scriptCode = '@echo off\n' + forceQuotes(sourceBinary.replace('/', '\\')) + ' ' + binaryArgs + ' %*\n'
		putFileContents(wrapperLocation, scriptCode)
	else:
		scriptCode = '#!/usr/bin/env sh\n' + forceQuotes(sourceBinary) + ' ' + binaryArgs + ' $@\n'
		putFileContents(wrapperLocation, scriptCode)
		os.chmod(wrapperLocation, stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

# Checks that all of the build prerequisites for the toolchain are met
def checkBuildPrerequisites():
	
	# Verify that git and cmake are installed
	errorIfNotAvailable('git')
	errorIfNotAvailable('cmake')
	
	# If the C++ compiler used by cmake is clang, verify that it doesn't suffer from bug #23381
	compiler = cxxCompiler()
	if isClang(compiler) and doesClangSuffer23381(compiler):
		print('Error: the version of clang being used suffers from bug 23381, which will break compilation.')
		print('Please update clang to a build that incorporates the fix from LLVM trunk, revision 261297:')
		print('<http://llvm.org/viewvc/llvm-project?view=revision&revision=261297>')
		sys.exit(1)

# Checks that all of the prerequisites are met for generating the installer package
def checkInstallerPrerequisites():
	if platform.system() == 'Windows':
		errorIfNotAvailable('makensis', versionFlag='/VERSION')
	else:
		errorIfNotAvailable('zip')		

# Builds the SPIR-V compiler and associated tools from source
def buildFromSource(rootDir):
	
	# Create the root directory to hold the build
	os.makedirs(rootDir)
	os.makedirs(rootDir + '/built')
	
	# Build the SPIR-V enabled version of clang
	runOrFail(['git', 'clone', '-b', 'khronos/spirv-3.6.1', 'https://github.com/KhronosGroup/SPIRV-LLVM.git', 'llvm-src'], cwd=rootDir)
	runOrFail(['git', 'clone', '-b', 'spirv-1.1', 'https://github.com/KhronosGroup/SPIR', 'clang'], cwd=rootDir + '/llvm-src/tools')
	os.makedirs(rootDir + '/llvm-src/build')
	runOrFail(['cmake', '-DCMAKE_INSTALL_PREFIX=' + os.path.abspath(rootDir) + '/built', '-DCMAKE_BUILD_TYPE=Release', '-G', GENERATOR, '..'], cwd=rootDir + '/llvm-src/build')
	runOrFail(['cmake', '--build', '.'], cwd=rootDir + '/llvm-src/build')
	runOrFail(['cmake', '--build', '.', '--target', 'install'], cwd=rootDir + '/llvm-src/build')
	
	# Download the OpenCL C++ standard library
	runOrFail(['git', 'clone', 'https://github.com/KhronosGroup/libclcxx.git', 'libclcxx'], cwd=rootDir)
	putFileContents(rootDir + '/libclcxx/test/CMakeLists.txt', '')
	runOrFail(['cmake', '-DCMAKE_INSTALL_PREFIX=' + os.path.abspath(rootDir) + '/built', '-G', GENERATOR, '.'], cwd=rootDir + '/libclcxx')
	runOrFail(['cmake', '--build', '.'], cwd=rootDir + '/libclcxx')
	runOrFail(['cmake', '--build', '.', '--target', 'install'], cwd=rootDir + '/libclcxx')
	
	# Build the SPIR-V tools, which includes the disassembler, so we can view the generated modules in text form
	runOrFail(['git', 'clone', 'https://github.com/KhronosGroup/SPIRV-Tools.git', 'tools-src'], cwd=rootDir)
	runOrFail(['git', 'clone', 'https://github.com/KhronosGroup/SPIRV-Headers.git', 'external/spirv-headers'], cwd=rootDir + '/tools-src')
	os.makedirs(rootDir + '/tools-src/build')
	runOrFail(['cmake', '-DCMAKE_INSTALL_PREFIX=' + os.path.abspath(rootDir) + '/built', '-DCMAKE_BUILD_TYPE=Release', '-G', GENERATOR, '..'], cwd=rootDir + '/tools-src/build')
	runOrFail(['cmake', '--build', '.'], cwd=rootDir + '/tools-src/build')
	runOrFail(['cmake', '--build', '.', '--target', 'install'], cwd=rootDir + '/tools-src/build')

# Creates the installer for the built SPIR-V compiler and associated tools
def createInstaller(rootDir):
	
	# The target directories
	installerDir = rootDir + '/installer'
	spirvDir = installerDir + '/spirv/1.1'
	wrapperDir = installerDir + '/wrappers'
	
	# Remove any previously-generated installer
	if os.path.exists(installerDir) == True:
		shutil.rmtree(installerDir)
	
	# Create the required directories
	makeDirs(installerDir)
	makeDirs(wrapperDir)
	makeDirs(spirvDir + '/bin')
	makeDirs(spirvDir + '/include')
	makeDirs(spirvDir + '/lib')
	
	# Copy the binaries (under macOS and Linux, copy the real clang binary, not any of its symlinks)
	clangBinary = 'clang' if (platform.system() == 'Windows') else 'clang-3.6'
	shutil.copy2(rootDir + '/built/bin/' + clangBinary + BINEXT, spirvDir + '/bin/spirv-clang' + BINEXT)
	binaries = ['spirv-as', 'spirv-cfg', 'spirv-dis', 'spirv-opt', 'spirv-val']
	for binary in binaries:
		shutil.copy2(rootDir + '/built/bin/' + binary + BINEXT, spirvDir + '/bin/' + binary + BINEXT)
	
	# Copy libclcxx
	shutil.copytree(rootDir + '/built/include/openclc++', spirvDir + '/include/openclc++')
	
	# Copy the clang lib folder, which includes opencl.h
	shutil.copytree(rootDir + '/built/lib/clang', spirvDir + '/lib/clang')
	
	# Generate the convenience wrappers for spirv-clang
	spirvDirTemplate = '%~dp0.\\..\\spirv\\1.1' if (platform.system() == 'Windows') else '__SPIRV_DIR__'
	libclcxxDirFlag = forceQuotes('-I' + spirvDirTemplate + '/include/openclc++')
	if platform.system() == 'Windows':
		libclcxxDirFlag = libclcxxDirFlag.replace('/', '\\')
	commonCompilerArgs = '-cc1 -emit-spirv -triple spir-unknown-unknown -x cl '
	createWrapper(wrapperDir + '/spirv-cc',  spirvDirTemplate + '/bin/spirv-clang', commonCompilerArgs + '-cl-std=CL2.0 -include opencl.h')
	createWrapper(wrapperDir + '/spirv-c++', spirvDirTemplate + '/bin/spirv-clang', commonCompilerArgs + '-cl-std=c++ ' + libclcxxDirFlag)
	
	# Under Windows, we use wrappers in place of symlinks for the binaries
	if platform.system() == 'Windows':
		createWrapper(wrapperDir + '/spirv-clang', spirvDirTemplate + '/bin/spirv-clang', '')
		createWrapper(wrapperDir + '/spirv-as',    spirvDirTemplate + '/bin/spirv-as',    '')
		createWrapper(wrapperDir + '/spirv-cfg',   spirvDirTemplate + '/bin/spirv-cfg',   '')
		createWrapper(wrapperDir + '/spirv-dis',   spirvDirTemplate + '/bin/spirv-dis',   '')
		createWrapper(wrapperDir + '/spirv-opt',   spirvDirTemplate + '/bin/spirv-opt',   '')
		createWrapper(wrapperDir + '/spirv-val',   spirvDirTemplate + '/bin/spirv-val',   '')
	
	# Generate the installer package
	if platform.system() == 'Windows':
		shutil.copy2(os.getcwd() + '/install-windows.nsi', installerDir + '/install.nsi')
		runOrFail(['makensis', 'install.nsi'], cwd=installerDir)
	else:
		installerScript = installerDir + '/install.sh'
		platformFriendlyName = 'macOS' if (platform.system() == 'Darwin') else 'linux'
		shutil.copy2(os.getcwd() + '/install-unix.sh', installerScript)
		os.chmod(installerScript, stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
		runOrFail(['zip', '-r9', './spirv-toolchain-' + platformFriendlyName + '.zip', './spirv', './wrappers', './install.sh'], cwd=installerDir)
	
	# Inform the user of the output directory location
	print('Installation package generated in `' + installerDir + '`')

# Cleans up the intermediate files generated during a run
def cleanupFiles(rootDir):
	shutil.rmtree(rootDir + '/llvm-src')
	shutil.rmtree(rootDir + '/libclcxx')
	shutil.rmtree(rootDir + '/tools-src')
	shutil.rmtree(rootDir + '/built')

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--keep-files', action='store_true', help='Keep intermediate files instead of deleting them')
parser.add_argument('--package-only', action='store_true', help='Generate the installer from the result of a previous run')
args = parser.parse_args()

# Determine if files from a previous run are available
rootDir = os.getcwd() + '/spirv-installer'
previousFilesExist = os.path.exists(rootDir + '/built/bin/clang' + BINEXT)

# Unless requested otherwise, build the SPIR-V toolchain
if args.package_only == False or previousFilesExist == False:
	checkBuildPrerequisites()
	buildFromSource(rootDir)

# Generate the installer
checkInstallerPrerequisites()
createInstaller(rootDir)

# Unless requested otherwise, remove the intermediate files
if args.keep_files == False:
	cleanupFiles(rootDir)
