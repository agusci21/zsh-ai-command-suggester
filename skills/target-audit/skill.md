# Target Enumeration & Local Audit Skill

## Triggers
- Queries about auditing a specific target machine, discovering services, or evaluating vulnerabilities on a local VM/host (e.g., lab targets, CTFs, local laptops/PCs).

## Inspection Strategy
- If a target hostname or remote machine name is given (e.g. "faci-portatil"):
  * NEVER use the local machine IP from Host Environment/Network Interfaces.
  * Resolve the target IP first via mDNS: `EXEC: getent hosts <hostname>.local | awk '{print $1}'`
  * Or search in ARP/neighbor cache: `EXEC: ip neighbor | grep -i <hostname> | awk '{print $1}'`
- If no IP is resolved, fall back to subnet discovery: `EXEC: ip -br addr`

## Rules & Syntax Constraints
- Enumeration flow:
  * Full port discovery: `nmap -p- -T4 --min-rate 1000 <target_ip>`
  * Service & version detection: `nmap -sV -sC -p <ports> <target_ip>`
  * Vulnerability script assessment: `nmap -sV --script vuln -p <ports> <target_ip>`
- Policy:
  * All scanning and probing commands require explicit execution confirmation.