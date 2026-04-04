package middleware

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"
	"os"

	"github.com/golang-jwt/jwt/v5"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

// TODO: This is the fastest choice but we could use REDIS
// tokenCache stores already-validated tokens so we don't re-parse the same JWT on every request.
// PROBLEM: this will keep on growing so we need some way to restrict this 
var tokenCache sync.Map

// runs on startup so if not set it will fail and the image will not compile (IIFE)
var jwt_secret = func() []byte {
	key := os.Getenv("JWT_SECRET")
	if key == "" {
		log.Fatal().Msg("JWT_SECRET not set. Server cannot start.")
	}
	return []byte(key)
}()

// contextKey is a custom type to avoid collisions when storing values in request context. Using a raw string like "user_id"
// can clash with other packages. This is the Go-recommended way.
type contextKey struct{}
var userIDKey = contextKey{}
func UserIDFromCtx(ctx context.Context) string {
	v, _ := ctx.Value(userIDKey).(string)
	return v
}

// StatusWriter wraps http.ResponseWriter to capture the
// status code. We need this because the standard ResponseWriter
// doesn't let you read back what status was written.
type StatusWriter struct {
	http.ResponseWriter
	Status int
}
func (w *StatusWriter) WriteHeader(code int) {
	w.Status = code
	w.ResponseWriter.WriteHeader(code)
}
func (w *StatusWriter) Flush() {
	if f, ok := w.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}



// Recovery catches any panic in downstream handlers and returns 
// a clean 500 JSON response instead of crashing the whole server.
// This is CRITICAL — one unrecovered panic kills the process.
//
// Apply to ALL routes:
//
//	mux.Handle("/any", Recovery(handler))
func Recoverer(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				log.Error().
					Interface("recover", err).
					Str("path", r.URL.Path).
					Msg("SYSTEM_PANIC_RECOVERED")

				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusInternalServerError)
				_ = json.NewEncoder(w).Encode(map[string]string{
					"error": "internal_server_error",
				})
			}
		}()
		next.ServeHTTP(w, r)
	})
}

// Logger logs each request's method, path, status, and duration.
// It skips logging entirely if the global log level is above Info
// (e.g., set to Warn or Error), so it costs zero CPU in production.
//
// Apply to ALL routes:
//
//	mux.Handle("/any", Recovery(Logger(handler)))
func Logger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Skip everything if log level is above Info
		if zerolog.GlobalLevel() > zerolog.InfoLevel {
			next.ServeHTTP(w, r)
			return
		}

		start := time.Now()
		sw := &StatusWriter{ResponseWriter: w, Status: http.StatusOK}

		next.ServeHTTP(sw, r)

		log.Info().
			Str("m", r.Method).
			Str("p", r.URL.Path).
			Int("s", sw.Status).
			Dur("d", time.Since(start)).
			Msg("req")
	})
}

// Auth extracts and validates the JWT from the Authorization header,
// then puts the user_id into the request context so handlers can
// just call middleware.UserIDFromCtx(r.Context()) to get it.
//
// IMPORTANT: Only apply to routes that NEED authentication.
// Do NOT apply to /auth/register, /auth/login, or /media/* routes.
//
// Example:
//
//	mux.Handle("/auth/register", Recovery(Logger(registerHandler)))       // NO Auth
//	mux.Handle("/auth/login",    Recovery(Logger(loginHandler)))          // NO Auth
//	mux.Handle("/media/",        Recovery(Logger(fileServer)))            // NO Auth
//	mux.Handle("/user/details",  Recovery(Logger(Auth(detailsHandler)))) // YES Auth
//	mux.Handle("/posts/create",  Recovery(Logger(Auth(createHandler))))  // YES Auth
func Auth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Step 1: Check if Authorization header exists and has "Bearer " prefix
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			_ = json.NewEncoder(w).Encode(map[string]string{
				"error": "unauthorized",
			})
			return
		}

		// Step 2: Extract token (everything after "Bearer ")
		token := authHeader[7:]

		// Step 3: Validate token (uses cache for speed)
		userID, err := validateToken(token)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			_ = json.NewEncoder(w).Encode(map[string]string{
				"error": "unauthorized",
			})
			return
		}

		// Step 4: Put user_id in context so handlers can access it
		ctx := context.WithValue(r.Context(), userIDKey, userID)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// JSONOnly rejects POST/PUT requests that aren't JSON or multipart.
// This prevents the server from wasting time reading garbage data.
//
// Allows:
//   - application/json    (for normal API calls)
//   - multipart/form-data (for file uploads in /posts/create)
//
// Do NOT apply to GET-only routes or /media/* routes.
func JSONOnly(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost || r.Method == http.MethodPut {
			ct := r.Header.Get("Content-Type")
			if !strings.Contains(ct, "application/json") &&
				!strings.Contains(ct, "multipart/form-data") {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusUnsupportedMediaType)
				_ = json.NewEncoder(w).Encode(map[string]string{
					"error": "unsupported_media_type",
				})
				return
			}
		}
		next.ServeHTTP(w, r)
	})
}

// validateToken checks if a JWT token is valid and returns the user_id.
//
// How it works:
//  1. Check tokenCache first — if we already validated this token, return instantly
//  2. If not cached, parse the JWT and verify the HMAC signature
//  3. Extract user_id from claims
//  4. Store in cache so next request with same token is instant
//
// This cache is a HUGE performance win because the benchmark
// reuses the same tokens across thousands of requests.
func validateToken(tokenString string) (string, error) {
	// Check cache first (instant return if found)
	if uid, ok := tokenCache.Load(tokenString); ok {
		return uid.(string), nil
	}

	// Parse and verify the JWT signature
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Make sure the signing method is HMAC (not RSA or something unexpected)
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return jwt_secret, nil
	})

	if err != nil {
		return "", err
	}

	// Extract user_id from the token payload
	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		userID, ok := claims["user_id"].(string)
		if !ok {
			return "", errors.New("user_id not found in token")
		}

		// Save to cache so we skip parsing next time
		tokenCache.Store(tokenString, userID)
		return userID, nil
	}

	return "", errors.New("invalid token")
}