// FILE: cmd/api/main.go
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
	chiMiddleware "github.com/go-chi/chi/v5/middleware"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"

	"backend-optimizer/internal/database"
	"backend-optimizer/internal/handlers"
	appMiddleware "backend-optimizer/internal/middleware"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// --- Postgres ---
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgres://postgres:password123@db:5432/socialdb?sslmode=disable"
	}

	poolCfg, err := pgxpool.ParseConfig(dbURL)
	if err != nil {
		log.Fatalf("Unable to parse DATABASE_URL: %v\n", err)
	}
	poolCfg.MaxConns = 100
	poolCfg.MinConns = 10

	dbPool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v\n", err)
	}
	defer dbPool.Close()

	// --- Redis ---
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis:6379"
	}
	rdb := redis.NewClient(&redis.Options{
		Addr:     redisURL,
		PoolSize: 50,
	})
	defer rdb.Close()

	// --- Dependency injection ---
	db := database.NewPostgres(dbPool)
	cache := database.NewRedisCache(rdb)
	h := handlers.NewHandler(db, cache)

	// --- Router ---
	r := chi.NewRouter()
	r.Use(chiMiddleware.Recoverer)

	// Serve uploaded media files
	mediaFS := http.StripPrefix("/media/", http.FileServer(http.Dir("/root/media")))
	r.Get("/media/*", mediaFS.ServeHTTP)

	// Health
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		if err := dbPool.Ping(r.Context()); err != nil {
			w.WriteHeader(http.StatusInternalServerError)
			w.Write([]byte("DB Offline"))
			return
		}
		w.Write([]byte("OK"))
	})

	// Auth (no auth middleware)
	r.Post("/auth/register", h.Register)
	r.Post("/auth/login", h.Login)

	// Authenticated routes
	r.Group(func(r chi.Router) {
		r.Use(appMiddleware.Auth(cache))

		// User
		r.Get("/user/details", h.UserDetails)
		r.Post("/user/delete", h.UserDelete)
		r.Get("/user/get_posts", h.UserGetPosts)
		r.Get("/user/liked_posts", h.UserLikedPosts)

		// Posts
		r.Post("/posts/create", h.PostCreate)
		r.Get("/posts/details", h.PostDetails)
		r.Post("/posts/delete", h.PostDelete)
		r.Post("/posts/like", h.PostLike)
	})

	// --- Start Server ---
	srv := &http.Server{
		Addr:         ":8080",
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		fmt.Println("🚀 Backend Optimizer API starting on :8080")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %s\n", err)
		}
	}()

	<-ctx.Done()
	fmt.Println("\nShutting down gracefully...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}
}