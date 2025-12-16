#!/usr/bin/env bash
set -euo pipefail

PIXEL_STREAMING_URL="${PIXEL_STREAMING_URL:-ws://127.0.0.1:8888}"
USE_XVFB="${USE_XVFB:-1}"
DISPLAY_VALUE="${DISPLAY:-:99}"
XVFB_RESOLUTION="${XVFB_RESOLUTION:-1920x1080x24}"
ULIMIT_NOFILE_VALUE="${ULIMIT_NOFILE:-1048576}"

HOST_LIBRARY_PATHS_DEFAULT="/host-libs/usr/lib/x86_64-linux-gnu:/host-libs/lib/x86_64-linux-gnu:/host-libs/usr/lib/nvidia:/host-libs/lib64:/host-libs/usr/lib64"
IFS=":" read -r -a HOST_LIBRARY_PATHS <<< "${HOST_LIB_PATHS:-$HOST_LIBRARY_PATHS_DEFAULT}"
for path in "${HOST_LIBRARY_PATHS[@]}"; do
  if [ -d "${path}" ]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}${path}"
  fi
done

if [ -z "${VK_ICD_FILENAMES:-}" ] && [ -f /host-libs/usr/share/vulkan/icd.d/nvidia_icd.json ]; then
  export VK_ICD_FILENAMES="/host-libs/usr/share/vulkan/icd.d/nvidia_icd.json"
fi

if [ -z "${VK_LAYER_PATH:-}" ]; then
  layer_dirs=(
    "/host-libs/usr/share/vulkan/implicit_layer.d"
    "/host-libs/usr/share/vulkan/explicit_layer.d"
  )
  accumulated=()
  for dir in "${layer_dirs[@]}"; do
    if [ -d "${dir}" ]; then
      accumulated+=("${dir}")
    fi
  done
  if [ ${#accumulated[@]} -gt 0 ]; then
    export VK_LAYER_PATH="$(IFS=:; echo "${accumulated[*]}")"
  fi
fi

OPENCV_RUNTIME_DIR="/opt/embody/Engine/Plugins/Runtime/OpenCV/Binaries/ThirdParty/Linux/x86_64-unknown-linux-gnu/opencv/lib"
if [ -d "${OPENCV_RUNTIME_DIR}" ]; then
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}${OPENCV_RUNTIME_DIR}"
fi

xvfb_pid=""
embody_pid=""
cleanup() {
  set +e
  if [ -n "${embody_pid}" ] && kill -0 "${embody_pid}" 2>/dev/null; then
    kill "${embody_pid}" 2>/dev/null || true
    wait "${embody_pid}" 2>/dev/null || true
  fi
  if [ -n "${xvfb_pid}" ] && kill -0 "${xvfb_pid}" 2>/dev/null; then
    kill "${xvfb_pid}" 2>/dev/null || true
    wait "${xvfb_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [ "${USE_XVFB}" != "0" ]; then
  mkdir -p /tmp/.X11-unix || true
  chmod 1777 /tmp/.X11-unix 2>/dev/null || true
  echo "Starting Xvfb on ${DISPLAY_VALUE} with ${XVFB_RESOLUTION}"
  Xvfb "${DISPLAY_VALUE}" -screen 0 "${XVFB_RESOLUTION}" &
  xvfb_pid=$!
  export DISPLAY="${DISPLAY_VALUE}"
else
  echo "USE_XVFB=0, not starting Xvfb"
fi

ulimit -n "${ULIMIT_NOFILE_VALUE}" || true

cd /opt/embody

if [ -n "${EMBODY_EXTRA_ARGS:-}" ]; then
  # shellcheck disable=SC2086
  set -- ${EMBODY_EXTRA_ARGS} "$@"
fi

./Embody.sh -RenderOffScreen -PixelStreamingURL="${PIXEL_STREAMING_URL}" -Log "$@" &
embody_pid=$!
wait "${embody_pid}"
