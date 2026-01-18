# submodules

kegscraper uses a number of submodules to separate the implementations for different services.

As of writing, here are some example submodules:

- bromcom: Interact with [bromcom](https://bromcomvle.com)
- it: Interact with [the kegs IT website](https://it.kegs.org.uk)
- kerboodle: Interact with [kerboodle](https://kerboodle.com)
- oliver: Interact with [oliver (the library system)](https://kegs.oliverasp.co.uk/)
- papercut: Interact with [Papercut MF (printer info. only available on the KEGS network)](https://printing.kegs.local:9191)
- site: Interact with [the KEGS website](https://kegs.org.uk)
- vle: Interact with [kegsNET](https://vle.kegs.org.uk)

You can import a submodule using `from kegscraper import {name}`, replacing `{name}` with the submodule name.
e.g.: `from kegscraper import site` to import the api for the main website
