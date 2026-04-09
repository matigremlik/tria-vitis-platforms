#! /bin/sh -e
WPA_DAEMON="/usr/sbin/wpa_supplicant"
CONF_FOLDER="/usr/share/wpa_ap"
AP_IFACE="wlan0"
WPA_OPTION="-c $CONF_FOLDER/wpa_ap_actual.conf -i$AP_IFACE"
WPA_PID="/var/run/wpa_${AP_IFACE}.pid"
SSD_OPTIONS="--quiet --pidfile $WPA_PID --exec $WPA_DAEMON -- $WPA_OPTION"

DNSMASQ_PID="/var/run/dnsmasq-${AP_IFACE}.pid"
DNSMASQ_LEASES="/var/lib/misc/udhcpd.leases"
AP_IP="192.168.2.1"

get_ap_mac_compact() {
  if [ -r "/sys/class/net/$AP_IFACE/address" ]; then
    tr -d ':' < "/sys/class/net/$AP_IFACE/address"
    return 0
  fi

  ip link show "$AP_IFACE" 2>/dev/null | awk '/link\/ether/ {gsub(":", "", $2); print $2; exit}'
}

do_start() {
  modprobe wilc-sdio

  while ! ip link show "$AP_IFACE" > /dev/null 2>&1
  do
    sleep 1
  done

  ip link set "$AP_IFACE" down || true
  ip addr flush dev "$AP_IFACE" || true

  hid="$(get_ap_mac_compact)"
  [ -n "$hid" ] || hid="UNKNOWN"

  ssid="Ultra96-V2_${hid}"
  esc_ssid="$(printf '%s\n' "$ssid" | sed 's/[&|]/\\&/g')"

  sed "s|Ultra96|$esc_ssid|g" "$CONF_FOLDER/wpa_ap.conf" > "$CONF_FOLDER/wpa_ap_actual.conf"

  start-stop-daemon --start --background --make-pidfile $SSD_OPTIONS
  sleep 1

  ip addr replace "$AP_IP/24" dev "$AP_IFACE"
  ip link set "$AP_IFACE" up

  mkdir -p /var/lib/misc
  touch "$DNSMASQ_LEASES"
  dnsmasq \
    --port=0 \
    --interface="$AP_IFACE" \
    --bind-interfaces \
    --dhcp-range=192.168.2.2,192.168.2.254,255.255.255.0,10d \
    --dhcp-option=option:router,$AP_IP \
    --dhcp-leasefile="$DNSMASQ_LEASES" \
    --pid-file="$DNSMASQ_PID"
}

do_stop() {
  if [ -f "$DNSMASQ_PID" ]; then
    kill "$(cat "$DNSMASQ_PID")" 2>/dev/null || true
    rm -f "$DNSMASQ_PID"
  fi

  start-stop-daemon --stop --quiet --pidfile "$WPA_PID" || true
  rm -f "$CONF_FOLDER/wpa_ap_actual.conf"
}

case "$1" in
  start)
    echo -n "Starting Ultra96 AP setup daemon... "
    do_start
    echo "done."
    ;;
  stop)
    echo -n "Stopping Ultra96 AP setup daemon..."
    do_stop
    echo "done."
    ;;
  *)
    echo "Usage: /etc/init.d/ultra96-ap-setup.sh {start|stop}"
    exit 1
esac

exit 0
