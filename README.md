SPIR-V Toolchain Installer
==========================

This Python script downloads and builds the [Khronos OpenCL C++ compiler for SPIR-V](https://github.com/KhronosGroup/SPIR/tree/spirv-1.1) and the [SPIR-V Tools](https://github.com/KhronosGroup/SPIRV-Tools) from source, and generates a platform-specific installation package.


Prerequisites
-------------

The following tools are required to be in the system PATH:

- [Python](https://www.python.org/) 3.x
- [Git](https://git-scm.com/)
- [Cmake](https://cmake.org/)
- A C++11-compliant compiler:
    - GCC or Clang under macOS and Linux
    - Visual Studio under Windows (be sure to run `vcvarsall.bat` to add `cl.exe` to the PATH)
- `zip` under macOS and Linux
- [Nullsoft Scriptable Install System (NSIS)](http://nsis.sourceforge.net/) under Windows (preferably the [64-bit version](https://bitbucket.org/dgolub/nsis64))


Generating the installer
------------------------

To generate the installation package for your platform, simply run:

```
python3 generate-installer.py
```

Under Windows, an installer executable is generated. To install, simply run the installer.

Under macOS and Linux, a ZIP file is generated that contains the required files and an installation script. To install, extract the ZIP file, and then run the following command inside the directory where the files were extracted:

```
sudo ./install.sh
```


Compiling OpenCL kernels
------------------------

In addition to installing the SPIR-V-enabled version of Clang under the name `spirv-clang`, two convenience wrappers are also provided to simplify compilation of OpenCL kernels:

- `spirv-cc` invokes `spirv-clang` with the necessary arguments for compiling OpenCL C code
- `spirv-c++` invokes `spirv-clang` with the necessary arguments for compiling OpenCL C++ code 

### Compiling OpenCL C Code

Assume we have the following OpenCL C code in the file `example-c.cl`:

```
__kernel void example()
{
    int globalThreadIdx = get_global_id(0);
    printf("This is thread %s", globalThreadIdx);
}
```

We can compile the kernel using `spirv-clang` directly like so:

```
spirv-clang -cc1 -emit-spirv -triple spir-unknown-unknown -x cl -cl-std=CL2.0 -include opencl.h example-c.cl -o example-c.spv
```

Or we can compile it using the convenience wrapper like so:

```
spirv-cc example-c.cl -o example-c.spv
```

### Compiling OpenCL C++ Code

Assume we have the following OpenCL C++ code in the file `example-cxx.cl`:

```
#include <opencl_work_item>
#include <opencl_printf>

__kernel void example()
{
    int globalThreadIdx = cl::get_global_id(0);
    cl::printf("This is thread %s", globalThreadIdx);
}
```

We can compile the kernel using `spirv-clang` directly like so (note that the path to the `openclc++` headers directory will vary based on the platform. Under macOS and Linux the installer places it in `/usr/local/spirv/1.1/include/openclc++`, under Windows with the default install location it will be in `C:\Program Files\SPIR-V\spirv\1.1\include\openclc++`):

```
spirv-clang -cc1 -emit-spirv -triple spir-unknown-unknown -x cl -cl-std=c++ -I/path/to/openclc++ example-cxx.cl -o example-cxx.spv
```

Or we can compile it using the convenience wrapper like so:

```
spirv-c++ example-cxx.cl -o example-cxx.spv
```


License
-------

The Python script is licensed under the MIT License. See the repositories for the [Khronos OpenCL C++ compiler for SPIR-V](https://github.com/KhronosGroup/SPIR/tree/spirv-1.1) and the [SPIR-V Tools](https://github.com/KhronosGroup/SPIRV-Tools) for the license details of those projects.
