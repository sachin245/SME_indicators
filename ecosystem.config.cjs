module.exports = {
  apps: [
    {
      name: "sme-indicators",
      script: "/home/admin/apps/sme-indicators/venv/bin/uvicorn",
      args: "api.main:app --host 0.0.0.0 --port 6002",
      cwd: "/home/admin/apps/sme-indicators",
      interpreter: "none",
      env: {
        PYTHONPATH: "/home/admin/apps/sme-indicators",
        // numpy needs libopenblas; system one is missing and we can't sudo-install.
        // Pi runs 32-bit armhf user space on a 64-bit kernel — use the armhf .so
        // extracted from the libopenblas0 deb to ~/.local/openblas/.
        LD_LIBRARY_PATH:
          "/home/admin/.local/openblas/usr/lib/arm-linux-gnueabihf/openblas-pthread:" +
          "/home/admin/.local/openblas/usr/lib/arm-linux-gnueabihf",
      },
      restart_delay: 3000,
      max_restarts: 5,
    },
  ],
};
