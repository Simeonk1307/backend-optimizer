package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"time"

	"backend-optimizer/internal/models"
	"github.com/golang-jwt/jwt/v5"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/oklog/ulid/v2"
)

var jwtSecret = []byte(os.Getenv("JWT_SECRET"))

func init() {
	if len(jwtSecret) == 0 {
		panic("JWT_SECRET environment variable is not set")
	}
}

func generateToken(userID string) (string, error) {
	claims := jwt.MapClaims{
		"user_id": userID,
		"exp":     time.Now().Add(time.Hour * 24).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(jwtSecret)
}

func (h *Handler) Register(w http.ResponseWriter, r *http.Request) {
	var req models.RegisterRequest
	
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields() 
	if err := decoder.Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid_json_schema"})
		return
	}

	var res models.RegisterResponse
	
	// Generate ULID with u_ prefix
	userID := "u_" + ulid.Make().String()

	query := `
		INSERT INTO users (user_id, username, password, display_name) 
		VALUES ($1, $2, $3, $4) 
		RETURNING user_id, username, display_name`
	
	err := h.DB.QueryRow(r.Context(), query, userID, req.Username, req.Password, req.DisplayName).
		Scan(&res.UserID, &res.Username, &res.DisplayName)

	if err != nil {
		// Check if it's a unique constraint violation (username already exists)
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) {
			// 23505 = unique_violation in PostgreSQL
			if pgErr.Code == "23505" {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusConflict)
				json.NewEncoder(w).Encode(map[string]string{"error": "user_exists"})
				return
			}
			// 23514 = check_violation
			if pgErr.Code == "23514" {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusBadRequest)
				json.NewEncoder(w).Encode(map[string]string{"error": "invalid_input"})
				return
			}
		}
		// Other database errors
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "internal_error"})
		return
	}

	token, err := generateToken(res.UserID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "token_generation_failed"})
		return
	}
	res.Token = token

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated) 
	json.NewEncoder(w).Encode(res)
}

func (h *Handler) Login(w http.ResponseWriter, r *http.Request) {
	var req models.LoginRequest

	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()

	if err := decoder.Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid_json_schema"})
		return
	}

	var userID string
	var storedPassword string
	
	err := h.DB.QueryRow(r.Context(), 
		"SELECT user_id, password FROM users WHERE username = $1", 
		req.Username).Scan(&userID, &storedPassword)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(map[string]string{"error": "unauthorized"})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "internal_error"})
		return
	}

	if storedPassword != req.Password {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(map[string]string{"error": "unauthorized"})
		return
	}

	token, err := generateToken(userID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "token_generation_failed"})
		return
	}

	// Cache token in Redis for auth middleware
	h.Redis.Set(r.Context(), "auth:"+token, userID, 24*time.Hour)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(models.LoginResponse{
		UserID: userID,
		Token:  token,
	})
}