#!/bin/bash
# Creates the read-only role the agent connects with. This is the real safety layer:
# even if validation is bypassed, the role cannot write and queries die after 5s.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE ${READONLY_USER} LOGIN PASSWORD '${READONLY_PASSWORD}'
  NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER ROLE ${READONLY_USER} SET statement_timeout = '5s';
ALTER ROLE ${READONLY_USER} SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${READONLY_USER};
GRANT USAGE ON SCHEMA public TO ${READONLY_USER};
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
  GRANT SELECT ON TABLES TO ${READONLY_USER};
EOSQL
