# Local operation

Follow README.md for installation and launch. Build the frontend before starting the backend. Use 127.0.0.1:8765 for the combined application, or Vite on 5173 during development.

No hosted deployment is configured. The local application has no authentication and must remain bound to loopback. Public hosting requires a separate authentication, TLS, credentials and access-control design.

Before backup, stop the backend cleanly, then copy data/studio.sqlite3. Keep the old data directory intact during transition. Do not overwrite the new database with a legacy schema. No automated legacy migration is supplied.
