FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI:append = " \
  file://0001-drop-protobuf-logsilencer.patch \
  file://0002-drop-protobuf-logsilencer-xnnpp.patch \
  file://0003-link-absl-for-protobuf4.patch \
  file://0004-disable-tests-samples-when-build-test-off.patch \
  file://0005-link-absl-globally-for-vai-add-library.patch \
  file://0006-find-absl-config.patch \
  file://0007-include-cstdint-clocs-scatter.patch \
"

PACKAGECONFIG:remove = "python test"
EXTRA_OECMAKE:append = " -DBUILD_PYTHON=OFF -DBUILD_TEST=OFF"
