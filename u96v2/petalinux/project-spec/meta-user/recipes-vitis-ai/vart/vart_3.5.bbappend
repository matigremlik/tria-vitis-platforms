FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI:append = " \
  file://0001-xrt-fallback-when-xclipname2index-missing.patch \
  file://0002-include-cstdint-util-4bit.patch \
  file://0003-include-cstdint-core-headers.patch \
  file://0004-include-cstdint-trace-headers.patch \
  file://0005-fix-gcc13-array-bounds-batch-tensor.patch \
  file://0006-fix-gcc13-array-bounds-runner-assistant.patch \
  file://0007-xrt-legacy-api-compat-shim.patch \
  file://0008-disable-xrt-device-handle-tests.patch \
  file://0009-buffer-object-xrt-legacy-bo-compat.patch \
  file://0010-dpu-controller-xrt-legacy-local-shim.patch \
  file://0011-runner-assistant-respect-build-test.patch \
  file://0012-restore-bo-wrappers-to-xrtbo.patch \
  file://0013-fix-xrt-compat-bo-handle-abi.patch \
  file://0014-reopen-local-xcl-handles-in-xrt-cu.patch \
  file://0015-buffer-object-local-xcl-handle.patch \
"

# Build VART in XRT/vitis-flow mode with Python bindings enabled.
# XRT 2024.2 drops legacy xcl* exports that VART 3.5 vitis-flow still uses.
PACKAGECONFIG:remove = "test"
PACKAGECONFIG:append = " python vitis"

# Build without tests, but keep Python module build on and point pybind11 lookup
# at the recipe sysroot include directory used for cross builds.
EXTRA_OECMAKE:append = " -DBUILD_TEST=OFF -DBUILD_PYTHON=ON -DPYBIND11_PATH=${RECIPE_SYSROOT}${includedir} -Dpybind11_DIR=${RECIPE_SYSROOT}${PYTHON_SITEPACKAGES_DIR}/pybind11/share/cmake/pybind11"

CXXFLAGS:append = " -I${RECIPE_SYSROOT}${PYTHON_SITEPACKAGES_DIR}/pybind11/include -include cstdint"

DEPENDS:append = " python3-pybind11 python3-numpy"
