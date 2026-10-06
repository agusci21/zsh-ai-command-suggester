# Nmap & Security Auditing Domain Skill

## Triggers
- Queries involving nmap, port scanning, network scanning, vulnerability scanning, NSE scripts, or host discovery.

## Inspection Strategy
- If the local network CIDR or interface IP is not provided in the query, inspect with: `EXEC: ip -br addr` or `EXEC: ip route`.
- If a custom script is requested (e.g. vulscan, vulners), verify its existence in NSE directory: `EXEC: ls /usr/share/nmap/scripts/*vuln* 2>/dev/null` or `EXEC: locate *.nse 2>/dev/null`.

## Rules & Syntax Constraints
- NSE script categories:
  * The official built-in category for vulnerability scanning is `vuln` (syntax: `--script vuln`).
  * Never invent script names like `vulnscan`. Third-party alternatives are `vulscan` or `vulners` (only if installed on the host).
- Flag compatibility:
  * NEVER combine `--script` with `-sn` or `-sP`. Vulnerability scripts require port scanning and service detection (`-sV`).
  * Standard comprehensive vulnerability scan command:
    `nmap -sV --script vuln <target_ip_or_subnet>`
  * Fast vulnerability scan with version detection:
    `nmap -sV -T4 --script vuln <target_ip_or_subnet>`
- Privileged operations:
  * SYN stealth scans (`-sS`), OS detection (`-O`), or raw packet scans require `sudo`.