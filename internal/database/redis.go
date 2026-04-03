package database

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
)

// RDB is the global Redis client. 
// It internally manages a connection pool, so we don't need to manually open/close 
// connections for every command.
var RDB *redis.Client

// InitRedis initializes the Redis client using the address provided (e.g., REDIS_URL).
func InitRedis(addr string) {
	// 1. Configure the Redis Client.
	// Unlike Postgres, go-redis builds the pool directly in the Options struct.
	RDB = redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: "", // Set this via os.Getenv if you add a password to your .env later
		DB:       0,  // Default DB index

		// OPTIMIZER SETTINGS:
		// PoolSize: Maximum number of socket connections. 
		// Match this to your expected high-concurrency load.
		PoolSize: 100,

		// MinIdleConns: Keeps 10 connections ready to go.
		// Prevents "latency spikes" when the benchmark starts.
		MinIdleConns: 10,

		// Timeouts: Critical for an "Optimizer" to prevent hanging the API.
		DialTimeout:  5 * time.Second,
		ReadTimeout:  3 * time.Second,
		WriteTimeout: 3 * time.Second,
	})

	// 2. VERIFICATION (Fail Fast)
	// We use a short timeout to ensure Redis is actually reachable.
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	if _, err := RDB.Ping(ctx).Result(); err != nil {
		log.Fatal().Err(err).Msg("Redis is configured but unreachable. Check your Docker network.")
	}

	log.Info().
		Str("addr", addr).
		Int("pool_size", 100).
		Msg("Redis Client initialized and verified")
}

// CloseRedis gracefully closes the Redis connection pool.
// Use 'defer database.CloseRedis()' in your main.go.
func CloseRedis() {
	if RDB != nil {
		if err := RDB.Close(); err != nil {
			log.Error().Err(err).Msg("Error closing Redis client")
		}
	}
}