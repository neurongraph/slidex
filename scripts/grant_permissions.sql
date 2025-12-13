-- Grant permissions on all tables to the connecting user
-- This allows external tools like DBeaver to access the tables

-- Replace 'your_username' with the username you're using in DBeaver
-- Common usernames: postgres, your_system_username, or the user shown in DBeaver

-- Grant on existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO PUBLIC;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO PUBLIC;

-- Grant on future tables (for new tables created later)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO PUBLIC;

-- If you want to grant to a specific user instead of PUBLIC, use:
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sdas;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sdas;
