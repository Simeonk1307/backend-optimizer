package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

func main() {
	// 1. Setup Context for Gracious Shutdown
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// 2. Initialize Postgres Connection Pool (High Performance)
	dbURL := os.Getenv("DATABASE_URL")
	dbPool, err := pgxpool.New(ctx, dbURL)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v\n", err)
	}
	defer dbPool.Close()

	// 3. Initialize Redis Client
	redisURL := os.Getenv("REDIS_URL")
	rdb := redis.NewClient(&redis.Options{
		Addr: redisURL,
	})
	defer rdb.Close()

	// 4. Setup Router
	r := chi.NewRouter()
	r.Use(middleware.Logger)    // Helps you see requests in Docker logs
	r.Use(middleware.Recoverer) // Prevents the whole app from crashing on one bad request

	// 5. Define Endpoints
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		// Optimization Check: Can we ping the DB?
		err := dbPool.Ping(r.Context())
		if err != nil {
			w.WriteHeader(http.StatusInternalServerError)
			w.Write([]byte("DB Offline"))
			return
		}
		w.Write([]byte("OK"))
	})

	// 6. Start Server in a Goroutine
	srv := &http.Server{
		Addr:    ":8080",
		Handler: r,
	}

	go func() {
		fmt.Println("🚀 Backend Optimizer API starting on :8080")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %s\n", err)
		}
	}()

	// 7. Wait for Interrupt (Control+C or Docker Down)
	<-ctx.Done()
	fmt.Println("\nShutting down gracefully...")
	
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}
}