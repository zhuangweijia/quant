## ADDED Requirements

### Requirement: Application validates critical configuration at startup

The system SHALL validate all critical configuration items during application startup (FastAPI lifespan). The following items MUST be validated:

1. `ENCRYPTION_KEY` MUST be a non-empty string that can construct a valid Fernet instance
2. JWT private key file (`JWT_PRIVATE_KEY_PATH`) MUST exist and be readable
3. JWT public key file (`JWT_PUBLIC_KEY_PATH`) MUST exist and be readable
4. Database connection MUST be established successfully (execute `SELECT 1`)

If any validation fails, the system SHALL log a clear error message indicating which configuration item failed and why, then refuse to start (`sys.exit(1)`).

#### Scenario: All configurations valid
- **WHEN** all critical configuration items are present and valid
- **THEN** the application starts normally without errors

#### Scenario: ENCRYPTION_KEY is empty
- **WHEN** `ENCRYPTION_KEY` is an empty string or not set
- **THEN** the application logs an error "ENCRYPTION_KEY is not configured" and refuses to start

#### Scenario: ENCRYPTION_KEY is invalid
- **WHEN** `ENCRYPTION_KEY` is set but cannot construct a valid Fernet instance
- **THEN** the application logs an error "ENCRYPTION_KEY is invalid" and refuses to start

#### Scenario: ENCRYPTION_KEY cannot decrypt existing data
- **WHEN** `ENCRYPTION_KEY` is set and can construct a valid Fernet instance
- **AND** there are existing encrypted records in the `settings` table (where `encrypted = true`)
- **AND** decrypting any of those records with the current key fails
- **THEN** the application logs an error "ENCRYPTION_KEY does not match existing encrypted data - possible key mismatch" and refuses to start

#### Scenario: No existing encrypted data to verify
- **WHEN** `ENCRYPTION_KEY` is valid and there are no existing encrypted records in the database
- **THEN** the validation passes (skip decrypt-check)

#### Scenario: JWT key file missing
- **WHEN** the file at `JWT_PRIVATE_KEY_PATH` or `JWT_PUBLIC_KEY_PATH` does not exist
- **THEN** the application logs an error indicating the missing file and refuses to start

#### Scenario: Database connection failed
- **WHEN** the database connection cannot be established
- **THEN** the application logs an error with the connection details and refuses to start

#### Scenario: Skip validation in development
- **WHEN** environment variable `SKIP_CONFIG_VALIDATION` is set to `true`
- **THEN** the startup validation is skipped and the application starts regardless of configuration issues
