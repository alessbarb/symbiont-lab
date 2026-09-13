# Safety Boundaries

Symbiont is a defensive organism developed in a controlled research repository.
Cognition, threats, reporters and interventions remain synthetic. The only permitted
real-host interaction is explicit, local and read-only capability discovery.

## Permitted host discovery

- Discover which local, read-only senses the current runtime can safely expose.
- Record capability metadata that contains no hostname, username, address, path,
  credential or user content.
- Isolate platform-specific probes behind the OS-agnostic `symbiont.host` contract.
- Fail closed when a provider requests write, execute or remote scope.
- Keep the resulting manifest visible and reproducible.

## Absolute prohibitions

1. **No remote discovery or network scanning:** no host enumeration, socket
   listeners, packet injection, port scanning or discovery of neighboring devices.
2. **No exploitation or evasion:** no shellcode, privilege escalation, concealment,
   persistence, credential access or bypass of platform protections.
3. **No autonomous real-world actions:** no process termination, file modification,
   quarantine, command execution or configuration changes.
4. **No covert collection:** no hostname, username, user paths, file contents,
   messages, keystrokes, media, tokens or payloads.
5. **No uncontrolled propagation:** Symbiont never installs or copies itself to
   another environment.
