FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

inherit python3-dir

DEPENDS += "python3 python3-native python3-pybind11"
RDEPENDS:${PN} += "python3"
FILES:${PN} += "${PYTHON_SITEPACKAGES_DIR}/pyxrt* ${PYTHON_SITEPACKAGES_DIR}/*.py"
# pyxrt gets stripped during build; suppress already-stripped QA for this package
INSANE_SKIP:${PN} += "already-stripped"

# Point CMake at Yocto's python3/pybind11 in the target sysroot
EXTRA_OECMAKE:append = " \
  -DPython3_EXECUTABLE:FILEPATH=${STAGING_BINDIR_NATIVE}/python3-native/python3 \
  -DPython3_ROOT_DIR:PATH=${STAGING_DIR_TARGET}/usr \
  -DPython3_INCLUDE_DIRS:PATH=${STAGING_DIR_TARGET}/usr/include/python${PYTHON_BASEVERSION} \
  -DPython3_LIBRARY:FILEPATH=${STAGING_DIR_TARGET}/usr/lib/libpython${PYTHON_BASEVERSION}.so \
  -DPython3_LIBRARIES:FILEPATH=${STAGING_DIR_TARGET}/usr/lib/libpython${PYTHON_BASEVERSION}.so \
  -DPython3_FIND_STRATEGY=LOCATION \
  -DPython3_FIND_REGISTRY=NEVER \
  -DPython3_FIND_FRAMEWORK=NEVER \
  -Dpybind11_DIR:PATH=${STAGING_DIR_TARGET}/usr/lib/python${PYTHON_BASEVERSION}/site-packages/pybind11/share/cmake/pybind11 \
  -DXRT_INSTALL_PYTHON_DIR:PATH=${PYTHON_SITEPACKAGES_DIR} \
  -DPYBIND11_USE_CROSSCOMPILING=ON \
  -DPYTHON_IS_DEBUG=OFF \
  -DPYTHON_MODULE_EXTENSION=.cpython-312-aarch64-linux-gnu.so \
  -DPYTHON_MODULE_DEBUG_POSTFIX= \
  -DPYBIND11_PYTHON_VERSION=${PYTHON_BASEVERSION} \
"

do_configure:prepend() {
  local cmake_es="${S}/CMake/embedded_system.cmake"
  if ! grep -q "xrt_add_subdirectory(python)" "${cmake_es}"; then
    sed -i '/add_subdirectory(runtime_src)/a\
\
# --- Python bindings ---\
xrt_add_subdirectory(python)\
' "${cmake_es}"
  fi

  local cmake_py="${S}/python/pybind11/CMakeLists.txt"
  # Respect a pre-set Python3_EXECUTABLE in cross builds
  if grep -q "# Virtual environment detected, use its Python" "${cmake_py}"; then
    perl -0pi -e 's/if \(DEFINED ENV\{VIRTUAL_ENV\}\)\n    # Virtual environment detected, use its Python\n    set\(Python3_EXECUTABLE \$ENV\{VIRTUAL_ENV\}\/bin\/python3\)\n    message\(STATUS "Virtual environment detected, using Python3: \${Python3_EXECUTABLE}"\)\n  else\(\)\n    # No virtual environment, use system Python3\n    # In alma 8.10 python3.11 comes as a dependency but still pybind11 is installed to default python3\.\n    set\(Python3_EXECUTABLE \/usr\/bin\/python3\)\n  endif\(\)/if (NOT DEFINED Python3_EXECUTABLE)\n  if (DEFINED ENV\{VIRTUAL_ENV\})\n    # Virtual environment detected, use its Python\n    set(Python3_EXECUTABLE \$ENV\{VIRTUAL_ENV\}\/bin\/python3)\n    message(STATUS "Virtual environment detected, using Python3: \${Python3_EXECUTABLE}")\n  else()\n    # No virtual environment, use system Python3\n    set(Python3_EXECUTABLE \/usr\/bin\/python3)\n  endif()\nendif()/s' "${cmake_py}"
  fi

  # Don't require interpreter in cross builds; use dev headers/libs only
  if grep -q "find_package(Python3 COMPONENTS Development Interpreter)" "${cmake_py}"; then
    sed -i 's/find_package(Python3 COMPONENTS Development Interpreter)/find_package(Python3 COMPONENTS Development)/' "${cmake_py}"
  fi

  if ! grep -q "NOT PKGDIR" "${cmake_py}"; then
    perl -0pi -e 's/find_package\(pybind11 2\.6\.0 REQUIRED PATHS/if (NOT PKGDIR)\n    set(PKGDIR "site-packages")\n  endif()\n  find_package(pybind11 2.6.0 REQUIRED PATHS/' "${cmake_py}"
  fi

  if ! grep -q "INCLUDE_DIRECTORIES(${Python3_INCLUDE_DIRS})" "${cmake_py}"; then
    sed -i '/INCLUDE_DIRECTORIES(\${PYTHON_INCLUDE_PATH})/a\  INCLUDE_DIRECTORIES(${Python3_INCLUDE_DIRS})' "${cmake_py}"
  fi
}

# Provide a compatibility wrapper for legacy scripts that still call `xdputil`.
do_install:append() {
  install -d ${D}${bindir}
  cat > ${D}${bindir}/xdputil <<'EOS'
#!/bin/sh
# xdputil compatibility wrapper (XRT 2024.x uses xbutil/xrt-smi)
if command -v xbutil >/dev/null 2>&1; then
  if [ "$1" = "query" ]; then
    shift
    exec xbutil examine "$@"
  fi
  exec xbutil "$@"
fi

echo "xdputil: xbutil not found" >&2
exit 127
EOS
  chmod 0755 ${D}${bindir}/xdputil
}
