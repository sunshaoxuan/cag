# Final receipt

Release: 0.9.1

Status: implementation, automated tests, production build, deployment and
browser acceptance complete.

Delivered:

* Correct long-term memory governance panel padding
* Aligned heading and governance label
* Bordered and centered empty-state surface
* Component regression assertions
* Updated frontend design and release documentation

Rollback:

1. Deploy version 0.9.0.
2. Remove `memory-console` and `memory-empty` from the Memory page.
3. Restore the 0.9.0 frontend image.

No database rollback is required.
