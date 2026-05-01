# EC2 Database Transfer

One-time transfer of the local SQLite database to the EC2 instance.

## Prerequisites

- SSH access to EC2 (port 22 must be open in the security group)
- PEM file at `C:\Users\ResolveWave\Documents\GitHub\ec2-access.pem`
- `scp` / `ssh` available in terminal (`openssh` ships with Windows 10+)

## Run the transfer

```powershell
cd C:\Users\ResolveWave\Documents\GitHub\SME_indicators
.\transfer_db_to_ec2.ps1
```

The script will:

1. Confirm before overwriting anything
2. Stop `sme-api` on EC2 so SQLite is not locked during the copy
3. Back up the existing remote DB to `sme_indicators.db.bak_<timestamp>`
4. `scp` the local `data/sme_indicators.db` → `~/SME_indicators/data/sme_indicators.db`
5. Verify the remote file size matches the local file
6. Restart `sme-api`

## Connection details

| | |
|---|---|
| **EC2 IP** | `98.81.94.194` |
| **SSH user** | `ubuntu` |
| **PEM key** | `C:\Users\ResolveWave\Documents\GitHub\ec2-access.pem` |
| **Remote project path** | `~/SME_indicators` |
| **Remote DB path** | `~/SME_indicators/data/sme_indicators.db` |

## If port 22 is blocked

Open it in the AWS Console:

1. EC2 → Instances → select instance → **Security** tab → click the security group
2. **Inbound rules** → **Edit inbound rules**
3. Add rule: **SSH**, port **22**, source **My IP** (or `0.0.0.0/0` for open access)
4. Save — SSH will be available within seconds

## Manual transfer (without the script)

```powershell
# Stop the service
ssh -i "C:\Users\ResolveWave\Documents\GitHub\ec2-access.pem" ubuntu@98.81.94.194 "sudo systemctl stop sme-api"

# Copy the database
scp -i "C:\Users\ResolveWave\Documents\GitHub\ec2-access.pem" `
    data\sme_indicators.db `
    ubuntu@98.81.94.194:~/SME_indicators/data/sme_indicators.db

# Restart the service
ssh -i "C:\Users\ResolveWave\Documents\GitHub\ec2-access.pem" ubuntu@98.81.94.194 "sudo systemctl start sme-api"
```

## Notes

- The local DB is **~25 MB** — transfer takes a few seconds on a normal connection.
- After transfer, the EC2 instance serves the same data as your local environment.
- The backup (`*.bak_<timestamp>`) is kept on EC2 indefinitely; delete it manually once you've confirmed everything looks good.
