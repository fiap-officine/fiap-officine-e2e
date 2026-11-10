-- Uma instância PostgreSQL, dois bancos lógicos com usuários próprios
-- (mesmo modelo do RDS compartilhado em AWS).
CREATE ROLE os_service LOGIN PASSWORD 'os_service';
CREATE DATABASE os_db OWNER os_service;
REVOKE ALL ON DATABASE os_db FROM PUBLIC;

CREATE ROLE billing_service LOGIN PASSWORD 'billing_service';
CREATE DATABASE billing_db OWNER billing_service;
REVOKE ALL ON DATABASE billing_db FROM PUBLIC;
