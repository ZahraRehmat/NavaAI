# Popular website directory

`popular_websites.json` contains the first 10,000 accepted ASCII domains from
[Tranco list 8P8NV](https://tranco-list.eu/list/8P8NV), first generated on
8 November 2026. The list aggregates CrUX, Farsight, Majestic, Cloudflare Radar
and Cisco Umbrella rankings over the preceding 30 days.

Source CSV: https://tranco-list.eu/download/8P8NV/1000000

Attribution: Victor Le Pochat, Tom Van Goethem, Samaneh Tajalizadehkhoob,
Maciej Korczyński and Wouter Joosen. *Tranco: A Research-Oriented Top Sites
Ranking Hardened Against Manipulation*, NDSS 2019.
https://doi.org/10.14722/ndss.2019.23386

Provider attribution and source licensing are described on
https://tranco-list.eu/ (including CrUX CC BY-SA 4.0, Cloudflare Radar
CC BY-NC 4.0, and Majestic CC BY 3.0). This data is kept with its source
identity for reproducibility. Popularity includes technical domains and
does not establish homepage availability or endorse website contents.

Gwen reads this file locally. It does not fetch rankings, crawl these domains,
or contact them during recognition/lookup. Navigation occurs only in response
to a user command. Explicit HTTPS domain names continue working even when
absent from this list. Common spoken brand/web-app names are additionally
defined in `../website_aliases.json`.

Refresh manually with `python setup_website_directory.py --list-id 8P8NV`.
The updater validates a complete download before replacing existing data.
