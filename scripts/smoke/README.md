# Smoke scripts

Ad-hoc end-to-end checks that talk to a **running deployment** (they default to the
production Railway URL and create a throwaway `qa@test.com` account). They are not part
of the pytest suite or CI. Point them at a local or staging backend before running.
