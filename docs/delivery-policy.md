# Versioned Desktop delivery

User preference recorded 16 October 2026.

Keep only the current portable Windows ZIP and the full extracted application
folder at the Desktop root for this product. Preserve unrelated Desktop items.
Store reports and reference documents inside the current application folder.

Use `Quant Trading AI v<VERSION>` for the extracted application folder and
`Quant-Trading-AI-v<VERSION>-Windows-x64.zip` for its portable archive.
Source archives and release manifests must also include the exact version in
their names, but stay in the development output or inside the app folder rather
than adding Desktop root clutter.

Verify the running/bundled version and executable/archive hashes before removing
superseded Desktop deliveries. Preserve runtime financial journals and learning
data under LOCALAPPDATA/NEXUS. Never remove dependencies from the extracted app
or leave only the executable: the entire portable folder is required.

Stop a running instance through its local API before renaming its application
directory, retain broker stops, and restore its previous execution mode only
after account and ownership checks. Do not reset daily budgets or halts.
