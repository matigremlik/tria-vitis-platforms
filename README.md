# Important Info
Based on Tria Vitis Platforms original BSP availible here: https://github.com/AlbertaBeef/tria-vitis-platforms/tree/2024.2
Fixes a fair few issues present in the Ultra96 build paths due to depreciation and version incompatibility. Also by default includes 4 extra overlays that have an DPU and various HLS pre-processing kernels included. 

Report om the work contained within and on the background, availible at: [View the PDF](Report.pdf)

Running (petalinux24) petalinux-build in u96v2/petalinux will create a distro with all the overlays included. Generate the SD Card as below.

To change between overlays, run the following on the u96v2:

- APP=OVERLAYNAMEHERE
- mkdir -p /etc/dfx-mgrd
- echo "$APP" > /etc/dfx-mgrd/$APP
- ln -sf /etc/dfx-mgrd/$APP /etc/dfx-mgrd/default_firmware
- reboot

where OVERLAYNAMEHERE is the name of a valid overlay/app (can be checked via xmutil listapps), e.g tria-u96v2-accel-dpu-optimised

To enable wifi on-board:


systemctl stop ultra96-ap-setup
pkill wpa_supplicant || true
pkill dnsmasq || true
iw dev p2p0 del 2>/dev/null || true

cat >/tmp/ap-open.conf <<'EOF'
ctrl_interface=/var/run/wpa_supplicant
ap_scan=2
network={
    ssid="U96-OPEN"
    mode=2
    frequency=2412
    key_mgmt=NONE
}
EOF

wpa_supplicant -B -iwlan0 -c /tmp/ap-open.conf
ip addr replace 192.168.2.1/24 dev wlan0
ip link set wlan0 up
dnsmasq --port=0 --interface=wlan0 --bind-interfaces \
  --dhcp-range=192.168.2.2,192.168.2.254,255.255.255.0,10d \
  --dhcp-option=option:router,192.168.2.1 \
  --dhcp-leasefile=/var/lib/misc/udhcpd.leases \
  --pid-file=/var/run/dnsmasq-wlan0.pid

  # Original Read-me Bellow:

# Overview
Tria Vitis 2024.2 platforms and overlays.

# Documentation

The following series of Hackster projects describe how the 2023.2 version of this github repository was created, but still serves as documentation for the 2024.2 version:

[Part 1](https://avnet.me/tria-vitis-2023.2-part1) : Tria Vitis Platforms - Building the Foundational Designs

[Part 2](https://avnet.me/tria-vitis-2023.2-part2) : Tria Vitis Platforms - Creating a Common Platform

[Part 3](https://avnet.me/tria-vitis-2023.2-part3) : Tria Vitis Platforms - Adding support for Vitis-AI

[Part 4](https://avnet.me/tria-vitis-2023.2-part4) : Tria Vitis Platforms - Adding support for Hailo-8

[Part 5](https://avnet.me/tria-vitis-2023.2-part5) : Tria Vitis Platforms - Adding support for ROS2

The motivation of this series of projects is to enable users to create their own custom AI applications.

# Pre-Built Images

The pre-built petalinux BSPs and SD images are provided for convenience:

| Pre-Built Image                            | Link                                                                                                     | md5sum                           | 
| :----------------------------------------- | :------------------------------------------------------------------------------------------------------- | :------------------------------- |
| ZUBoard                                    |                                                                                                          |                                  |
| tria_zub1cg_2023_2_petalinux_20241029.bsp  | [http://avnet.me/tria-vitis-2023.2-zub1cg-petalinux](http://avnet.me/tria-vitis-2023.2-zub1cg-petalinux) | b27a7b782c855b9f86fc6b9b8349b14a |
| tria_zub1cg_2023_2_sdimage_20241029.img.gz | [http://avnet.me/tria-vitis-2023.2-zub1cg-sdimage](http://avnet.me/tria-vitis-2023.2-zub1cg-sdimage)     | 615c7603151ed52951ac3c6979b091b1 |
| Ultra96-V2                                 |                                                                                                          |                                  |
| tria_u96v2_petalinux_2023_2-2024-10-24.bsp | [http://avnet.me/tria-vitis-2023.2-u96v2-petalinux](http://avnet.me/tria-vitis-2023.2-u96v2-petalinux)   | 05dc1491e2a2ccee4c366d62dc1bc732 |
|                                            | [http://avnet.me/tria-vitis-2023.2-u96v2-sdimage](http://avnet.me/tria-vitis-2023.2-u96v2-sdimage)       |                                  |
| UltraZed-EV                                |                                                                                                          |                                  |
| tria_uz7ev_2023_2_petalinux_20241029.bsp   | [http://avnet.me/tria-vitis-2023.2-uz7ev-petalinux](http://avnet.me/tria-vitis-2023.2-uz7ev-petalinux)   | aac643f867133375bf4e6573791539c1 |
| tria_uz7ev_2023_2_sdimage_20241029.img.gz  | [http://avnet.me/tria-vitis-2023.2-uz7ev-sdimage](http://avnet.me/tria-vitis-2023.2-uz7ev-sdimage)       | 07f5186de7047f74854b2007cfcfb0b5 |


# Build Instructions

## Preparation

Clone repository:
- git clone --recursive --branch u96v2-vai35-fork https://github.com/matigremlik/tria-vitis-platforms
- cd tria-vitis-platforms

Download DPU IP:
- cd common/overlays
- source ./get_dpu_ip.sh
- cd ../..

Download prebuilt binaries for final SD image:
- cd common/sdcard/content
- source ./download_content.sh
- cd ../../..

## ZUBoard Instructions

Navigate to zub1cg directory:
- cd zub1cg

Build (all) the zub1cg vitis platforms:
- make platform PFM=zub1cg_sbc_minimal
- make platform PFM=zub1cg_sbc_base
- make platform PFM=zub1cg_sbc_dualcam
- make platform PFM=zub1cg_sbc_dualcam1
- make platform PFM=zub1cg_sbc_dualcam2

Build (all) the zub1cg vitis overlays:
- make overlay OVERLAY=benchmark
- make overlay OVERLAY=dualcam_dpu

Build the zub1cg petalinux project:
- make petalinux

Create the BOOT.BIN (without bitstream):
- cd petalinux
- petalinux-package --boot --fsbl --pmufw --u-boot --force
- cd ..

Create the final zub1cg SD card image:
- cd sdcard
- sudo ./generate_sdcard.sh

## Ultra96-V2 Instructions

Navigate to u96v2 directory:
- cd u96v2

Build (all) the u96v2 vitis platforms:
- make platform PFM=u96v2_sbc_minimal
- make platform PFM=u96v2_sbc_base
- make platform PFM=u96v2_sbc_dualcam
- make platform PFM=u96v2_sbc_dualcam1
- make platform PFM=u96v2_sbc_dualcam2

Build (all) the u96v2 vitis overlays:
- make overlay OVERLAY=benchmark
- make overlay OVERLAY=dualcam_dpu

Build the u96v2 petalinux project:
- make petalinux

Create the BOOT.BIN (without bitstream):
- cd petalinux
- petalinux-package --boot --fsbl --pmufw --u-boot --force
- cd ..

Create the final u96v2 SD card image:
- cd sdcard
- sudo ./generate_sdcard.sh

## UltraZed-7EV Instructions

Navigate to u96v2 directory:
- cd uz7ev

Build (all) the uz7ev vitis platforms:
- make platform PFM=uz7ev_sbc_base
- make platform PFM=uz7ev_sbc_nvme

Build (all) the uz7ev vitis overlays:
- make overlay OVERLAY=benchmark

Build the uz7ev petalinux project:
- make petalinux

Create the BOOT.BIN (without bitstream):
- cd petalinux
- petalinux-package --boot --fsbl --pmufw --u-boot --force
- cd ..

Create the final uz7ev SD card image:
- cd sdcard
- sudo ./generate_sdcard.sh





