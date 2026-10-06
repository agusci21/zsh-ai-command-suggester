# Network Domain Skill

## Triggers
- Queries involving IP addresses, subnets, open ports, routing, ping, nmap, or network interfaces.

## Inspection Strategy
- Never hardcode or assume subnets (e.g. 192.168.1.0/24).
- Use `EXEC: ip -br addr` or `EXEC: ip route` to discover actual live IP addresses and default gateways.
- Use `EXEC: ss -tuln` to inspect listening ports.

## Rules
- Use modern `ip` and `ss` commands instead of deprecated `ifconfig` or `netstat`.
- Favor fast discovery tools like `nmap -sn` for ping sweeps when scanning subnets.