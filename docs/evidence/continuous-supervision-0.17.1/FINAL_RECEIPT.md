# Version 0.17.1 final receipt

## Delivered

* System startup and user sign-in triggers.
* Long-running health supervisor.
* Missing-listener startup and sustained-failure recovery.
* Task Scheduler retry policy.
* Rotating supervisor logs.
* Successful SQLite to PostgreSQL pgvector cutover.
* Version 0.17.1 frontend and API deployment.

## Current runtime

The scheduled task is running under the current interactive Windows identity.
The Gateway is ready on all IPv4 interfaces. PostgreSQL, pgvector, Redis and
queue workers are healthy. The management page reports version 0.17.1.
Controlled recovery restored a stopped idle Gateway in 45.7 seconds.

ChatGPT subscription credentials remain bound to the configured Windows user.
The startup trigger becomes operational when that user's interactive token is
available, and the sign-in trigger provides the deterministic authenticated
startup path.

## Rollback

Run the management script with `stop` to stop the supervisor and recognized
Gateway. Use `uninstall` to remove the scheduled task. The original SQLite
source and migration reports remain available. PostgreSQL and its migration
receipt should be retained for comparison before any database rollback.
