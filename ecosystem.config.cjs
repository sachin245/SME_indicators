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
      },
      restart_delay: 3000,
      max_restarts: 5,
    },
  ],
};
