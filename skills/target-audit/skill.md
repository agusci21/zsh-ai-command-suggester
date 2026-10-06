# Target Enumeration & Local Audit Skill

## Triggers
- Queries about auditing a specific target machine, discovering services, or finding vulnerabilities on a local VM/host (e.g., lab targets, CTFs, VulnHub machines).

## Inspection Strategy
- If the target IP is unknown, search for active hosts in the local ARP/routing table or subnet:
  * `EXEC: ip -br addr`
  * `EXEC: ip neighbor`
- If local vulnerability databases exist, check tools availability (e.g., `which searchsploit`).

## Rules & Syntax Constraints
- Enumeration flow:
  * Full port discovery: `nmap -p- -T4 --min-rate 1000 <target_ip>`
  * Service & version detection on open ports: `nmap -sV -sC -p <ports> <target_ip>`
  * Vulnerability script scanning: `nmap -sV --script vuln -p <ports> <target_ip>`
- Version lookup:
  * If a service banner and version are identified, suggest querying local databases: `searchsploit "<service_name> <version>"`
- Policy:
  * All scanning and probing commands require explicit execution confirmation.