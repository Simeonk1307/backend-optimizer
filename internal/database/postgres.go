package database

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog/log"
)

// PPool holds the open "pipes" to the database so we don't reconnect every time.
var PPool *pgxpool.Pool

// InitPostgres sets up the connection pool using the address provided.
func InitPostgres(connStr string) {
	
	// 1. Convert the address string into a "Config" object we can tweak.
	config, err := pgxpool.ParseConfig(connStr)
	if err != nil {
		log.Fatal().Err(err).Msg("Database URL is broken or unreadable")
	}

	// 2. Tweak the pool for the Optimizer Competition.
	config.MaxConns = 250         // Total simultaneous workers (Stay under Docker's 300 limit).
	config.MinConns = 10          // Keep 10 pipes open immediately to avoid "startup lag".
	config.MaxConnIdleTime = 5 * time.Minute // Close unused pipes after 5 mins to save RAM.
	config.HealthCheckPeriod = 1 * time.Minute // Every minute, the pool checks if background connections are still alive.

	// 3. Create the actual Pool.
	// context.Background() ensures the pool stays alive as long as the app is running.
	PPool, err = pgxpool.NewWithConfig(context.Background(), config)
	if err != nil {
		log.Fatal().Err(err).Msg("Could not create the database pool")
	}

	// 4. Test the connection immediately (Fail Fast).
    // necessary as above may not err even if db is down
	// We give it 2 seconds to respond. If it fails, the app stops here.
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	if err := PPool.Ping(ctx); err != nil {
		log.Fatal().Err(err).Msg("Database is there, but refused our connection.")
	}

	log.Info().Msg("Postgres is ready and optimized.")
}

// Close shuts down all database pipes. 
// This should be "deferred" in main.go to run when the app stops.
func ClosePostgres() {
	if PPool != nil {
		PPool.Close()
	}
}