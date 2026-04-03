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

	"backend-optimizer/internal/database"
	// "backend-optimizer/internal/handlers"
	// appMiddleware "backend-optimizer/internal/middleware"
)

func mustGetEnv(key string) string {
	val := os.Getenv(key)
	if val == "" {
		// This kills the process and prints exactly what is missing
		log.Fatalf("FATAL: Environment variable %s is not set", key)
	}
	return val
}

func main() {
	// 1. Setup Signal Handling for Graceful Shutdown
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// 2. Strict Environment Loading (Fail Fast)
	dbURL := mustGetEnv("DATABASE_URL")
	rdURL := mustGetEnv("REDIS_URL")
	_ = mustGetEnv("JWT_SECRET") // We check it exists here; middleware uses it later


	// 3. Initialize Database Pools with cleanup on exit
	// These functions handle their own config and ping verification
	database.InitPostgres(dbURL)
	defer database.ClosePostgres()
	database.InitRedis(rdURL)
	defer database.CloseRedis()

	// 4. Dependency Injection
	// We pass the global pools directly from the database package
	// h := handlers.NewHandler(database.PPool, database.RDB)

	// 5. Router Setup
	r := chi.NewRouter()
	
	// Built-in Chi Middleware
	r.Use(chiMiddleware.Recoverer) // Prevents app crashes on panics
	r.Use(chiMiddleware.RealIP)    // Correctly identifies client IP

	// Serve media files - FIXED PATH to ./media to match Docker WORKDIR
	mediaFS := http.StripPrefix("/media/", http.FileServer(http.Dir("./media")))
	r.Get("/media/*", mediaFS.ServeHTTP)

	// Health Check - FIXED to use database.PPool
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		if err := database.PPool.Ping(r.Context()); err != nil {
			w.WriteHeader(http.StatusInternalServerError)
			w.Write([]byte("Postgres DB Offline"))
			return
		}
		w.Write([]byte("OK Postgres"))
	})

	// Health Check - FIXED to use database.PPool
	// Health Check - FIXED to use database.RDB correctly
    r.Get("/health-redis", func(w http.ResponseWriter, r *http.Request) {
        // .Ping() returns a *redis.StatusCmd
        // We call .Err() to see if the connection actually worked
        if err := database.RDB.Ping(r.Context()).Err(); err != nil {
            w.WriteHeader(http.StatusInternalServerError)
            w.Write([]byte("Redis DB Offline"))
            return
        }
        w.Write([]byte("OK Redis"))
    })

	// Public Routes
	// r.Post("/auth/register", h.Register)
	// r.Post("/auth/login", h.Login)

	// Authenticated Routes
	// r.Group(func(r chi.Router) {
		// FIXED: appMiddleware.Auth no longer needs 'cache' passed in 
		// because it uses the global database.RDB internally.
		// r.Use(appMiddleware.Auth)

	// 	// User Endpoints
	// 	r.Get("/user/details", h.UserDetails)
	// 	r.Post("/user/delete", h.UserDelete)
	// 	r.Get("/user/get_posts", h.UserGetPosts)
	// 	r.Get("/user/liked_posts", h.UserLikedPosts)

	// 	// Post Endpoints
	// 	r.Post("/posts/create", h.PostCreate)
	// 	r.Get("/posts/details", h.PostDetails)
	// 	r.Post("/posts/delete", h.PostDelete)
	// 	r.Post("/posts/like", h.PostLike)
	// })

	// 6. Server Configuration (Optimized Timeouts)
	srv := &http.Server{
		Addr:         ":8080",
		Handler:      r,
		ReadTimeout:  5 * time.Second,   // Tightened for benchmarks
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// 7. Start Server in a goroutine
	go func() {
		fmt.Printf("🚀 Backend Optimizer API starting on %s\n", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen error: %s\n", err)
		}
	}()

	// Wait for Interrupt
	<-ctx.Done()
	fmt.Println("\nShutting down gracefully...")

	// 8. Final Cleanup Context
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}
	fmt.Println("👋 Server stopped.")
}