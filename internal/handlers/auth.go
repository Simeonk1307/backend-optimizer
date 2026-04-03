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
	"github.com/oklog/ulid/v2"
	"golang.org/x/crypto/bcrypt"
)

var jwtSecret = []byte(os.Getenv("JWT_SECRET"))

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
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "invalid_json"}`, http.StatusBadRequest)
		return
	}

	var res models.RegisterResponse
	
	// Fast Bcrypt hash (cost 4)
	hashed, err := bcrypt.GenerateFromPassword([]byte(req.Password), 4)
	if err != nil {
		http.Error(w, `{"error": "internal_error"}`, http.StatusInternalServerError)
		return
	}

	// Generate ULID
	userID := "u_" + ulid.Make().String()

	query := `
		INSERT INTO users (user_id, username, password, display_name) 
		VALUES ($1, $2, $3, $4) 
		RETURNING user_id, username, display_name`
	
	err = h.DB.QueryRow(r.Context(), query, userID, req.Username, string(hashed), req.DisplayName).
		Scan(&res.UserID, &res.Username, &res.DisplayName)

	if err != nil {
		w.WriteHeader(http.StatusConflict)
		json.NewEncoder(w).Encode(map[string]string{"error": "user_exists"})
		return
	}

	res.Token, _ = generateToken(res.UserID)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(res)
}

func (h *Handler) Login(w http.ResponseWriter, r *http.Request) {
	var req models.LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "invalid_json"}`, http.StatusBadRequest)
		return
	}

	var userID string
	var storedPassword string
	
	err := h.DB.QueryRow(r.Context(), 
		"SELECT user_id, password FROM users WHERE username = $1", 
		req.Username).Scan(&userID, &storedPassword)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			http.Error(w, `{"error": "unauthorized"}`, http.StatusUnauthorized)
			return
		}
		http.Error(w, `{"error": "internal_error"}`, http.StatusInternalServerError)
		return
	}

	// Compare bcrypt hash
	if err := bcrypt.CompareHashAndPassword([]byte(storedPassword), []byte(req.Password)); err != nil {
		http.Error(w, `{"error": "unauthorized"}`, http.StatusUnauthorized)
		return
	}

	token, _ := generateToken(userID)

	// Pre-cache in Redis for the Auth middleware
	h.Redis.Set(r.Context(), "auth:"+token, userID, 24*time.Hour)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(models.LoginResponse{
		UserID: userID,
		Token:  token,
	})
}