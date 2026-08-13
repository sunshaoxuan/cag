# Final receipt

CAG 0.28.5 adds a periodic Windows watchdog trigger to the existing startup,
sign-in, health supervision and failure retry contract. Runtime, process
recovery, dependency connectivity, full automated tests and browser acceptance
have passed. The release commit is delivered directly from master and local
HEAD is compared with `origin/master` after the push.

The OneOps-configured primary port 8001 and fallback port 8002 are also Ready
and continuously supervised. The exact OneOps production connection function
returns success with one project for both endpoints. Authenticated OneOps UI
evidence remains missing because neither available browser surface provided a
usable authenticated automation session.
