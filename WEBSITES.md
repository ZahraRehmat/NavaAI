# Website commands

Gwen has a cached directory of **10,000 popular domains**, downloaded from
[Tranco list 8P8NV](https://tranco-list.eu/list/8P8NV), generated 8 November 2026.
Domain names, compact brand names, and common spoken aliases resolve locally.
The `.com`, `.org`, `.net`, `.pk`, etc. ending is optional for indexed names.

| Say or type | Result |
|---|---|
| open Wikipedia | Open Wikipedia using the current recognized browser, otherwise Chrome |
| open Wikipedia on Edge | Open Wikipedia in Edge |
| open stack overflow on Chrome | Open Stack Overflow in Chrome |
| open you tube dot com on Edge | Navigate to youtube.com in Edge |
| open Google Meet on Chrome | Open meet.google.com in Chrome |
| open GitHub website | Open the website rather than requesting an installed app |
| open booking on Edge | Resolve the downloaded domain name to booking.com |

Chrome and Edge reuse existing windows when available. If several windows of
the requested browser are open, Gwen asks which one to use. Grid on/off does
not change website routing. A website command bypasses grid mouse-name matching.
The reverted grid changes remain reverted.

Installed apps retain their existing opening priority for bare app names.
If a product also has an installed app, say **website**, include its domain,
or specify **on Chrome / on Edge**. File extensions and paths keep their
existing file routes, and generic targets such as `current`, `screenshots`,
`Word`, and `tab` are not reassigned to directory websites.

## Local files

- `data/popular_websites.json`: all 10,000 domains with their source ranks.
- `website_directory.py`: cached name lookup and conservative typo matching.
- `website_aliases.json`: editable HTTPS aliases for familiar names/web apps.
- `setup_website_directory.py`: explicit download/refresh utility.
- `data/WEBSITES_SOURCE.md`: provenance, source attribution and provider links.

To add a spoken name, add it to the alias list under the desired HTTPS URL in
`website_aliases.json`, then restart Gwen. Alias lookup ignores spaces and
punctuation, so `stack overflow` and `stackoverflow` share the same lookup.
Only uniquely strong one-character name typos are corrected; unresolved names
keep the normal direct-command behavior. No Qwen model is loaded.

## Recognition and lookup

The full directory works for typed/resolved names. Offline Vosk receives
supported dictionary words from the directory and bounded whole-command hints
for prominent names. It still depends on microphone quality and pronunciation;
indexing a domain does not add a new acoustic pronunciation to Vosk's model.
Dictation is not silently rewritten to a website name.

Directory lookup performs no network requests. Only the requested browser
navigation contacts a website. Popular-domain rankings include technical
domains; the directory does not claim that every entry has a human homepage
or that every site's availability has been tested.

## Verification

`test_website_directory.py` checks the complete directory, name/alias and
Chrome/Edge routing, spoken domains, file-path protection, grid passthrough,
existing-window reuse, local-only lookup, and voice vocabulary inclusion.
Five synthetic Windows SAPI samples resolved correctly in the development
run, with decoder times around 0.13–0.31 seconds. These are synthetic checks,
not measurements of human-accent accuracy.
