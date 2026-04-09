FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI:append = " \
  file://0001-include-cstdint.patch \
  file://0002-prefer-protobuf-config.patch \
"

DEPENDS:append = " python3-pybind11 python3-numpy"
RDEPENDS:${PN}:append = " python3-numpy"

# Ensure pybind11 headers and CMake config are found from sysroot site-packages
EXTRA_OECMAKE:append = " -Dpybind11_DIR=${RECIPE_SYSROOT}${PYTHON_SITEPACKAGES_DIR}/pybind11/share/cmake/pybind11 -DPYBIND11_PATH=${RECIPE_SYSROOT}${includedir}"
CXXFLAGS:append = " -I${RECIPE_SYSROOT}${PYTHON_SITEPACKAGES_DIR}/pybind11/include"

# Ensure pybind11 is found from the sysroot site-packages

do_configure:prepend() {
    cmake_py="${S}/../unilog/cmake/vai_add_pybind11_module.cmake"
    if [ -f "${cmake_py}" ]; then
        # Fix any broken path from earlier attempts
        sed -i "s|/usr/lib/python\./site-packages/pybind11/include|${PYTHON_SITEPACKAGES_DIR}/pybind11/include|g" "${cmake_py}"
        # Ensure the correct hint exists
        if ! grep -q "${PYTHON_SITEPACKAGES_DIR}/pybind11/include" "${cmake_py}"; then
            sed -i "/_PYBIND11_PATH pybind11/a\\        ${PYTHON_SITEPACKAGES_DIR}/pybind11/include" "${cmake_py}"
        fi
    fi
}
