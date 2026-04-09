# Force pmufw to pick the artifact name actually produced in this project.
# meta-xilinx-tools/pmufw-xsct.inc sets PMU_FIRMWARE_IMAGE_NAME = "pmu-firmware-${MACHINE}",
# but u96v2 flow emits pmu-firmware-zynqmp-pmu.{elf,bin}.
PMU_FIRMWARE_DEPLOY_DIR:forcevariable = "${DEPLOY_DIR_IMAGE}"
PMU_FIRMWARE_IMAGE_NAME:forcevariable = "pmu-firmware-zynqmp-pmu"
PMU_FILE:forcevariable = "${DEPLOY_DIR_IMAGE}/pmu-firmware-zynqmp-pmu"
